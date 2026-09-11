"""Offline synthetic scale gate. Run as python -m tests.pr30_checkpoint_benchmark.

Construction uses canonical writer envelopes and content-addressed fixture writes
without a per-write full audit. Timed replay/verification is entirely unmodified.
No network transport, production path, or provider credentials are used.
"""
import json
import platform
import tempfile
import time
from dataclasses import replace
from datetime import timedelta
from pathlib import Path

from forecast_prospective_projection import load_projection, rebuild_projection, assert_boundary, projection_path
from forecast_standalone_operations import NamespaceArchive, ManifestEntry, canonical_bytes, sha256_bytes
from forecast_standalone_activation import publish_verified_acquisition, canonical_mlb_schedule_request, encoded_kalshi_catalog_path, merge_mlb_schedule_responses, refresh_supporting_from_raw
from tests.test_forecast_supporting_replay import supporting_fixture


class SyntheticWriter(NamespaceArchive):
    def _commit_locked(self, *, raw_body, normalized, entry_values, **kwargs):
        raw_digest=sha256_bytes(raw_body);body=canonical_bytes(normalized);digest=sha256_bytes(body)
        entry=ManifestEntry.create(**entry_values,namespace=self.config.namespace,operating_mode=self.config.mode,
            raw_object_sha256=raw_digest,normalized_object_id='normalized:'+digest,normalized_schema_version=str(normalized['schema_version']))
        for family,identity,data in (('raw',raw_digest,raw_body),('normalized',digest,body),('manifest',entry.manifest_entry_id,canonical_bytes(entry))):
            path=self._path(family,identity);path.parent.mkdir(parents=True,exist_ok=True)
            if path.exists():
                assert path.read_bytes()==data
            else:path.write_bytes(data)
        return entry


def append_hour(archive, at, number, mlb, padding=260_000):
    day=json.loads(mlb)['dates'][0]['date']
    empty=b'{"cursor":"","markets":[]}'
    catalog=canonical_bytes({'cursor':'','markets':[], 'synthetic_response_metadata':str(number)+'x'*padding})
    with archive.mutation_lock():
        mlb_result=publish_verified_acquisition(archive=archive,provider='mlb-stats-api',union_raw=merge_mlb_schedule_responses((mlb,)),
            pages=((day,canonical_mlb_schedule_request(day)[1],mlb),),contracts=(),collected_at=at,
            protocol_id=None,command='refresh-supporting')
        publish_verified_acquisition(archive=archive,provider='kalshi',union_raw=empty,
            pages=(('', encoded_kalshi_catalog_path(''),catalog),),contracts=(),collected_at=at,
            protocol_id=None,command='refresh-supporting',dependencies=(mlb_result['acquisition_id'],))


def benchmark():
    with tempfile.TemporaryDirectory(prefix='pr30-synthetic-') as directory:
        archive,at=supporting_fixture(Path(directory),sessions=3,markets=1200)
        writer=SyntheticWriter(archive.config)
        from inspect_forecast_standalone_activation import fixtures
        mlb,_,_=fixtures();payload=json.loads(mlb)
        template=payload['dates'][0]['games'][0]
        payload['dates'][0]['games'].extend({**template,'gamePk':991000+i} for i in range(100))
        mlb=canonical_bytes(payload)
        refresh_supporting_from_raw(archive=writer,mlb_raw=mlb,kalshi_raw=b'{"cursor":"","markets":[]}',collected_at=at)
        initial_count=len(archive.entries())
        baseline_hours=(1866-initial_count+3)//4
        for hour in range(baseline_hours+720):
            append_hour(writer,at+timedelta(hours=hour+1),hour,mlb)
        boundary=at+timedelta(hours=baseline_hours+720)
        before=time.monotonic();cold=rebuild_projection(archive,boundary);build_seconds=time.monotonic()-before
        baseline=projection_path(archive).read_bytes()
        exact=[];delta=[];reads=[]
        for _ in range(5):
            before=time.monotonic();view,state=load_projection(archive,boundary)
            with archive.mutation_lock():assert_boundary(archive,view)
            exact.append(time.monotonic()-before)
            assert canonical_bytes(state)==canonical_bytes(cold)
        append_hour(writer,boundary+timedelta(hours=1),baseline_hours+720,mlb)
        final_at=boundary+timedelta(hours=1)
        for _ in range(5):
            projection_path(archive).write_bytes(baseline)
            before=time.monotonic();view,state=load_projection(archive,final_at)
            with archive.mutation_lock():assert_boundary(archive,view)
            delta.append(time.monotonic()-before);reads.append(len(view._bytes))
        before=time.monotonic();final_cold=rebuild_projection(archive,final_at);final_full_seconds=time.monotonic()-before
        assert canonical_bytes(state)==canonical_bytes(final_cold)
        assert max(exact+delta)<=7.5,(exact,delta)
        sources=[p for root in (archive.raw_root,archive.normalized_root) for p in root.glob('*/*')]
        result={'platform':platform.platform(),'machine':platform.machine(),'python':platform.python_version(),
            'fixture':'3 legacy/corrected sessions, paginated 1200-market catalogs; >=1866 baseline manifests plus 720 hourly MLB/Kalshi acquisitions and one measured delta',
            'graph_opportunities':len(final_cold.bucket('opportunities')),'baseline_hours':baseline_hours,'growth_hours':720,'selected_manifests':len(archive.entries()),
            'unique_source_objects':len(sources),'source_bytes':sum(p.stat().st_size for p in sources),
            'checkpoint_bytes':len(baseline),'full_build_seconds':build_seconds,'final_full_build_seconds':final_full_seconds,
            'exact_seconds':exact,'delta_seconds':delta,'delta_object_reads':reads,'canonical_state_sha256':sha256_bytes(canonical_bytes(final_cold)),
            'provider_requests':0,'limit_seconds':7.5,'passed':True}
        print(json.dumps(result,indent=2))


if __name__=='__main__':benchmark()
