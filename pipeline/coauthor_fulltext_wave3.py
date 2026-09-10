"""Isolated third coauthor-download wave using the tested import/review workflow."""
import argparse
from contextlib import contextmanager
import json
import threading

from common import ROOT
import coauthor_fulltext_wave2 as workflow

VERSION = "coauthor_update_wave3_2026_09_10"
PRIVATE, RESULTS = ROOT / "private" / VERSION, ROOT / "results" / VERSION
REVIEW_FIELDS = workflow.REVIEW_FIELDS
REVIEWERS = ("root", "participant")
LOCK = threading.RLock()


@contextmanager
def namespace():
    with LOCK:
        old = workflow.PRIVATE, workflow.RESULTS, workflow.REVIEWERS
        try:
            workflow.PRIVATE, workflow.RESULTS, workflow.REVIEWERS = PRIVATE, RESULTS, REVIEWERS
            yield
        finally:
            workflow.PRIVATE, workflow.RESULTS, workflow.REVIEWERS = old


def build():
    with namespace():
        return workflow.build()


def validate_shard(reviewer):
    with namespace():
        return workflow.validate_shard(reviewer)


def aggregate():
    with namespace():
        return workflow.aggregate()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-shard", choices=REVIEWERS)
    parser.add_argument("--aggregate", action="store_true")
    args = parser.parse_args()
    output = validate_shard(args.validate_shard) if args.validate_shard else aggregate() if args.aggregate else build()
    print(json.dumps(output, indent=2))
