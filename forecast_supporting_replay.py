"""Invocation-local full-namespace reads for ordinary supporting refresh.

Not a checkpoint, a persistent cache, or a collector authorization boundary.
All canonical validators still run. Prepared publication requires an unchanged
physical source inventory under the original namespace mutation lock.
"""
import json
from contextlib import contextmanager

from forecast_standalone_operations import (
    NamespaceArchive, OperationsError, canonical_bytes, reconcile_archive,
    replay_pr17_archive, sha256_bytes,
)
from forecast_prospective_projection import MAX_SOURCE_BYTES, _signature


class SupportingReplayArchive(NamespaceArchive):
    def __init__(self, archive):
        super().__init__(archive.config)
        self._archive = archive
        self._inventory = self._physical_inventory()
        self._bytes = {}
        self._json = {}
        self._decoded = {}
        self._verified = set()
        self._byte_count = 0
        self._entries = None
        self._integrity = None
        self._checks = {}
        self._publishing = False
        self._closed = False

    def _physical_inventory(self):
        return {path: _signature(path)
                for root in (self.raw_root, self.normalized_root,
                             self.manifest_root, self.temporary_root)
                for path in root.rglob('*') if path.is_file()}

    def assert_current(self):
        if self._closed or self._physical_inventory() != self._inventory:
            raise OperationsError('supporting-source-changed',
                                  'source changed during supporting preparation; no retry issued')

    def _assert_open(self):
        if self._closed:
            raise OperationsError('supporting-source-closed', 'invocation has ended')

    def _read_bytes(self, path):
        self._assert_open()
        if path in self._bytes:
            return self._bytes[path]
        before = _signature(path)
        if self._inventory.get(path) != before:
            raise OperationsError('supporting-source-changed', 'source identity changed')
        body = path.read_bytes()
        if _signature(path) != before:
            raise OperationsError('supporting-source-changed', 'source changed while reading')
        # Cache size is not a validity limit. Beyond it, use verified uncached reads.
        if self._byte_count + len(body) <= MAX_SOURCE_BYTES:
            self._bytes[path] = body
            self._byte_count += len(body)
        return body

    def _read_json(self, path):
        self._assert_open()
        if path not in self._json:
            value = json.loads(self._read_bytes(path))
            if path in self._bytes:
                self._json[path] = value
            return value
        return self._json[path]

    def read_verified(self, family, identity):
        path = self._path(family, identity)
        body = self._read_bytes(path)
        if path not in self._verified:
            if sha256_bytes(body) != identity.split(':')[-1]:
                raise OperationsError('archive-corrupt', str(path))
            if path in self._bytes:
                self._verified.add(path)
        return body

    def read_json_verified(self, family, identity):
        self.read_verified(family, identity)
        return self._read_json(self._path(family, identity))

    def _decode_manifest_path(self, path):
        self._assert_open()
        if path not in self._decoded:
            self._decoded[path] = super()._decode_manifest_path(path)
        return self._decoded[path]

    def entries(self):
        self._assert_open()
        if self._entries is None:
            self._entries = super().entries()
        return self._entries

    def prospective_entries(self):
        self._assert_open()
        # The generic replay hook's historical name does not mean filtering:
        # this view retains every namespace entry, including failures/publications.
        if self._integrity is None:
            self._integrity = reconcile_archive(self)
        if self._integrity.blocking:
            raise OperationsError('archive-integrity-failure',
                                  canonical_bytes(self._integrity).decode())
        allowed = set(self._integrity.authoritative_manifest_ids)
        return tuple(e for e in self.entries() if e['manifest_entry_id'] in allowed)

    def memoized_supporting_verification(self, key, verify):
        self._assert_open()
        if key not in self._checks:
            self._checks[key] = verify()
        return self._checks[key]

    @contextmanager
    def mutation_lock(self):
        if self._publishing or self._closed:
            raise OperationsError('supporting-source-closed', 'view is single-use')
        try:
            with self._archive.mutation_lock():
                self.assert_current()
                self._publishing = True
                yield
        finally:
            self._publishing = False
            self._closed = True

    def _ensure_mutable(self):
        raise OperationsError('supporting-source-read-only', 'use the fenced publication scope')

    def _publish(self, target, body):
        if not self._publishing or self._closed:
            raise OperationsError('supporting-source-read-only', 'publication requires the fence')
        created = self._archive._publish(target, body)
        self._inventory[target] = _signature(target)
        if target in self._bytes:
            self._byte_count -= len(self._bytes.pop(target))
        self._json.pop(target, None)
        self._decoded.pop(target, None)
        self._verified.discard(target)
        self._entries = self._integrity = None
        self._checks.clear()
        return created


def resolve_supporting_authority(archive, at):
    from forecast_standalone_activation import resolve_activated_authority
    view = SupportingReplayArchive(archive)
    state = replay_pr17_archive(view, analysis_boundary=at)
    with view.mutation_lock():
        return resolve_activated_authority(archive, at, state=state)
