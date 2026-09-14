#!/usr/bin/env python3
"""Manual saved MLB reports. No acquisition, server or collector state changes."""
import argparse
import json
import sys
from pathlib import Path

import forecast_reporting_delivery as delivery
from forecast_standalone_operations import DeploymentConfig, NamespaceArchive


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    sub = parser.add_subparsers(dest='command', required=True)
    for command in ('generate-historical', 'generate-live', 'update-live', 'verify', 'select-historical'):
        item = sub.add_parser(command)
        item.add_argument('--config', type=Path, required=True)
        if command in {'verify', 'select-historical'}:
            item.add_argument('--package', required=True)
            item.add_argument('--anchor', required=True, help='independent retained anchor key, not candidate-derived')
        else:
            item.add_argument('--expected-revision', required=True)
            item.add_argument('--status', choices=('in-progress', 'interim'), default='in-progress')
    item = sub.add_parser('open'); item.add_argument('--package')
    sub.add_parser('status')
    args = parser.parse_args(argv)
    try:
        if args.command == 'open':
            print(delivery.open_saved(output=args.output, package_id=args.package)); return 0
        if args.command == 'status':
            print(json.dumps(delivery.read_entry(args.output), indent=2)); return 0
        archive = NamespaceArchive(DeploymentConfig.from_json(args.config))
        if args.command == 'verify':
            value = delivery.verify_package(output=args.output, package_id=args.package, anchor_key=args.anchor, archive=archive)
        elif args.command == 'select-historical':
            value = delivery.select_historical(output=args.output, package_id=args.package, anchor_key=args.anchor, archive=archive)
        else:
            value = delivery.generate_report(output=args.output, archive=archive,
                study='historical' if args.command == 'generate-historical' else 'live',
                expected_revision=args.expected_revision, report_status=args.status, update_live=args.command == 'update-live')
        print(json.dumps(value, indent=2)); return 0
    except Exception as exc:
        print(f'Report command failed: {exc}', file=sys.stderr); return 1


if __name__ == '__main__':
    raise SystemExit(main())
