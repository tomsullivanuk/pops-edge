"""Activate a new display of retained verified packages; never replay/acquire source."""
import json
import os
import uuid
from dataclasses import fields
from datetime import datetime
from pathlib import Path

import forecast_reporting_delivery as delivery
import forecast_reporting_presentation as presentation
import forecast_reporting_collection as collection
from forecast_standalone_operations import canonical_bytes, sha256_bytes


def _retained(output, name, ref):
    package=output/'packages'/delivery._identity(ref['package_id'])
    _,payloads=delivery._inspect(package,ref['package_id'])
    anchor=delivery._read_anchor(output,ref['anchor_key'])
    report=delivery.analysis.deserialize_reporting_analysis(payloads['analysis.json'].decode())
    projections=delivery._json(payloads['projections.json']);envelope=delivery._json(payloads['envelope.json'])
    spec=report.context.computation
    if (report.object_id!=ref['report_id'] or spec.source_boundary_id!=anchor['boundary_id'] or
        spec.design_tag.value!=('prospective' if name=='live' else 'retrospective') or
        ref['report_status']!=report.context.report_status or
        ref['report_generated_at']!=report.context.report_generated_at.isoformat()):
        delivery._fail('selected display reference does not match retained report')
    receipts=[]
    for path in sorted((output/'receipts').glob('*.json')):
        if path.is_symlink():delivery._fail('verification receipt cannot be aliased')
        value=delivery._json(path.read_bytes())
        if all(value.get(k)==v for k,v in dict(package_id=ref['package_id'],anchor_key=ref['anchor_key'],
                report_id=report.object_id,source_boundary_id=anchor['boundary_id'],version=delivery.VERSION).items()):
            receipts.append((path,value))
    if not receipts:delivery._fail('selected package has no retained verification receipt')
    # JSON key sorting is not the original renderer's reconciliation row order.
    for scope,coverage in zip(projections['scopes'],report.coverages,strict=True):
        saved=scope['reconciliation']
        scope['reconciliation']={f.name:saved[f.name] for f in fields(coverage.reconciliation)}
    if delivery.render_report(report,projections,envelope)!=payloads['report.html']:
        delivery._fail('retained package renderer does not reconstruct')
    receipt_path,receipt=max(receipts,key=lambda x:x[1]['verified_at'])
    return report,projections,envelope,receipt_path,receipt


def _publish(output, previous, updated):
    if (output/'entry.html').read_bytes()!=previous:delivery._fail('entry changed during display preparation')
    temporary=output/('display-entry-'+uuid.uuid4().hex+'.partial')
    delivery._create(temporary,updated)
    try:os.replace(temporary,output/'entry.html')
    finally:temporary.unlink(missing_ok=True)
    delivery._sync_directory(output)


def activate_display(*,output,expected_revision,operational_state=None):
    output=delivery.validate_output_root(output)
    revision=delivery._revision(expected_revision)
    with delivery._local_writer(output):
        previous=(output/'entry.html').read_bytes();state=delivery.read_entry(output)
        if not all(state[name] for name in ('historical','live')):
            delivery._fail('display activation requires selected historical and live reports')
        selected={name:_retained(output,name,state[name]) for name in ('historical','live')}
        at=delivery.utc_now();identifier=uuid.uuid4().hex
        if any(datetime.fromisoformat(value[4]['verified_at'])>at for value in selected.values()):
            delivery._fail('display time precedes retained verification')
        observation=collection.snapshot(operational_state,at)
        displays=output/'displays'
        if displays.is_symlink():delivery._fail('display directory cannot be aliased')
        displays.mkdir(exist_ok=True);target=displays/identifier;target.mkdir()
        delivery._create(target/'previous-entry.html',previous)
        delivery._create(target/'saved-state.json',canonical_bytes(state))
        delivery._create(target/'collection-status.json',canonical_bytes(observation))
        delivery._create(target/'recovery.html',collection.recovery_page())
        repository=Path(__file__).resolve().parent
        for name,source in (('operator-guide.md','docs/MLB_REPORTING_DELIVERY_API_v1.2.0.md'),
                            ('collection-guide.md','operations/PROSPECTIVE_PROJECTION.md'),
                            ('deployment-guide.md','operations/PINNED_DEPLOYMENT.md')):
            delivery._create(target/name,(repository/source).read_bytes())
        def render(name,base,principal=False):
            report,projections,envelope,receipt_path,receipt=selected[name]
            relative=lambda path:os.path.relpath(path,base)
            links={key:relative(target/(key+'.html')) for key in ('live','historical')}
            title='Performance Report' if name=='live' else 'Historical candle report'
            other='historical' if name=='live' else 'live'
            body='<nav><a href="'+presentation.text(links[other])+'">'+('Historical candle report' if other=='historical' else 'Performance Report')+'</a></nav>'
            body+=presentation.update_notice(state)
            body+=presentation.summary(report,projections,envelope['synthetic_validation'],
                collection_status=collection.render(observation,relative(target/'recovery.html'),relative(target/'collection-status.json')))
            body+='<p class="muted">Display updated '+presentation.friendly(at)+'. Original calculation and evidence dates are unchanged; no new data was collected or scored.</p>'
            body+='<details><summary>Details</summary><p>Original report verified '+presentation.friendly(receipt['verified_at'])+'. This display uses that retained verification; it does not repeat scientific verification.</p>'
            prefix=relative(output/'packages'/state[name]['package_id'])+'/'
            body+=presentation.technical_contents(report,projections,envelope,prefix)
            body+=presentation.saved_reports(state,links,relative(target/'saved-state.json'))
            body+='<p><a download href="'+presentation.text(relative(receipt_path))+'">Download original verification receipt</a> · <a download href="'+presentation.text(relative(output/'anchors'/(state[name]['anchor_key']+'.json')))+'">Download retained source anchor</a> · <a download href="'+presentation.text(relative(target/'activation.json'))+'">Download display activation record</a></p></details>'
            if principal:
                body+='<script type="application/json" id="delivery-state">'+canonical_bytes(state).decode().replace('<','\\u003c')+'</script>'
            return presentation.page(title,body)
        for name in ('live','historical'):delivery._create(target/(name+'.html'),render(name,target))
        updated=render('live',output,True)
        receipt=dict(version='mlb-display-activation-1',activation_id=identifier,renderer_version=presentation.VERSION,
            software_revision=revision,rendered_at=at.isoformat(),previous_entry_sha256=sha256_bytes(previous),
            active_entry_sha256=sha256_bytes(updated),state=state,
            authority='display only; active exactly while entry bytes match active_entry_sha256',
            prior_verifications={name:selected[name][4] for name in selected},
            collection_display_version=collection.VERSION,
            collection_status_sha256=sha256_bytes(canonical_bytes(observation)))
        delivery._create(target/'activation.json',canonical_bytes(receipt))
        delivery._sync_directory(target)
        delivery._revision(revision)
        _publish(output,previous,updated)
        return receipt


def rollback_display(*,output,activation_id,expected_revision):
    output=delivery.validate_output_root(output);delivery._revision(expected_revision)
    with delivery._local_writer(output):
        target=output/'displays'/delivery._anchor_key(activation_id)
        if (output/'displays').is_symlink() or target.is_symlink():delivery._fail('aliased display rollback')
        for name in ('activation.json','previous-entry.html'):
            if (target/name).is_symlink():delivery._fail('aliased rollback record')
        receipt=delivery._json((target/'activation.json').read_bytes())
        current=(output/'entry.html').read_bytes();previous=(target/'previous-entry.html').read_bytes()
        if (receipt['activation_id']!=activation_id or sha256_bytes(current)!=receipt['active_entry_sha256'] or
            sha256_bytes(previous)!=receipt['previous_entry_sha256']):delivery._fail('rollback does not match current entry and retained backup')
        _publish(output,current,previous)
        result=dict(activation_id=activation_id,rolled_back_at=delivery.utc_now().isoformat(),entry_sha256=sha256_bytes(previous))
        delivery._create(target/('rollback-'+uuid.uuid4().hex+'.json'),canonical_bytes(result))
        return result
