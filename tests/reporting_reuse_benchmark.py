"""Offline reporting benchmark; all archive/output paths are disposable."""
import argparse
import json
import platform
import resource
import socket
import tempfile
import time
from contextlib import nullcontext
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

import forecast_reporting_delivery as delivery
import forecast_reporting_source as source
from forecast_standalone_operations import canonical_bytes, sha256_bytes
from forecast_standalone_activation import refresh_supporting_from_raw
from inspect_forecast_standalone_activation import fixtures
from tests.pr30_checkpoint_benchmark import SyntheticWriter, append_hour
from tests.test_forecast_supporting_replay import supporting_fixture
from tests.test_reporting_reconstruction_reads import UncachedReportingView


def emit(**fields):
    print(json.dumps(fields), flush=True)


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--target-manifests', type=int, default=6000)
parser.add_argument('--reference-original', action='store_true',
    help='Use original uncached source reads too; use a smaller fixture for a bounded comparison')
parser.add_argument('--cached-only', action='store_true',
    help='Measure only the final optimized end-to-end path at full scale')
args = parser.parse_args()
if args.target_manifests < 100:
    parser.error('target-manifests must be at least 100')

with tempfile.TemporaryDirectory(prefix='mlb-report-reuse-scale-') as directory, \
     patch.object(socket, 'socket', side_effect=AssertionError('provider/network forbidden')):
    root = Path(directory)
    emit(phase='fixture-start', root=str(root), platform=platform.platform())
    archive, at = supporting_fixture(root, sessions=3, markets=1200)
    writer = SyntheticWriter(archive.config)
    mlb, _, _ = fixtures()
    payload = json.loads(mlb)
    template = payload['dates'][0]['games'][0]
    payload['dates'][0]['games'].extend({**template, 'gamePk': 991000+i} for i in range(100))
    mlb = canonical_bytes(payload)
    refresh_supporting_from_raw(archive=writer, mlb_raw=mlb,
        kalshi_raw=b'{"cursor":"","markets":[]}', collected_at=at)
    hours = (args.target_manifests-len(archive.entries())+3)//4
    for hour in range(hours):
        append_hour(writer, at+timedelta(hours=hour+1), hour, mlb)
    boundary = at+timedelta(hours=hours, seconds=1)
    entries = archive.entries()
    sources = [p for base in (archive.raw_root, archive.normalized_root) for p in base.glob('*/*')]
    inventory_before = sorted((str(p.relative_to(archive.root)), sha256_bytes(p.read_bytes()))
                              for p in archive.root.rglob('*') if p.is_file())
    emit(phase='fixture-ready', manifests=len(entries), source_objects=len(sources),
         source_bytes=sum(p.stat().st_size for p in sources), hourly_acquisitions=hours)
    outputs = {}
    for reuse in ((True,) if args.cached_only else (True, False)):
        current = boundary
        def clock():
            global current
            current += timedelta(microseconds=1)
            return current
        counter = [0]
        original = source._reconstruct_uncached
        def counted(*args, **kwargs):
            counter[0] += 1
            emit(phase='reconstruct-start', reuse=reuse, number=counter[0])
            started = time.monotonic()
            result = original(*args, **kwargs)
            emit(phase='reconstruct-done', reuse=reuse, number=counter[0],
                 seconds=round(time.monotonic()-started, 3), objects=len(result[0].objects))
            return result
        started = time.monotonic()
        output = root/('cached' if reuse else 'uncached')
        reference_view = (patch.object(source, '_ReportingArchiveView', UncachedReportingView)
                          if not reuse and args.reference_original else nullcontext())
        with reference_view, patch.object(delivery, 'reporting_verification_scope',
                          source.reporting_verification_scope if reuse else nullcontext), \
             patch.object(source, '_reconstruct_uncached', side_effect=counted), \
             patch.object(archive, 'commit', side_effect=AssertionError('Evidence mutation forbidden')), \
             patch.object(archive, 'mutation_lock', side_effect=AssertionError('source locking forbidden')):
            ref = delivery.generate_report(archive=archive, output=output, study='live',
                expected_revision='d8e2fba7527b3a3ebd50902f3d44635dfdd84985',
                update_live=True, prepare_matches=True, clock=clock, synthetic_validation=True)
        hashes = {name:sha256_bytes((output/'packages'/ref['package_id']/name).read_bytes())
                  for name in ('source.json', 'analysis.json', 'projections.json', 'protocol.json')}
        match = json.loads((output/'matches'/(ref['package_id']+'.json')).read_bytes())
        hashes['match_rows'] = sha256_bytes(canonical_bytes(match['rows']))
        outputs[reuse] = hashes
        emit(phase='generation-done', reuse=reuse, seconds=round(time.monotonic()-started,3),
             reconstructions=counter[0], reference_original=args.reference_original,
             process_high_water_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
             hashes=hashes, provider_requests=0)
        assert counter[0] == (1 if reuse else 7)
    if not args.cached_only:
        assert outputs[True] == outputs[False]
    inventory_after = sorted((str(p.relative_to(archive.root)), sha256_bytes(p.read_bytes()))
                             for p in archive.root.rglob('*') if p.is_file())
    assert inventory_after == inventory_before
    emit(phase='passed', scientific_bytes_identical=None if args.cached_only else True,
         source_archive_unchanged=True,
         provider_requests=0)
