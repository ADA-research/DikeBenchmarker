"""This module provides an adaptor for executing checkers of sat or unsat certificates."""

import importlib.resources
import os

from DikeBenchmarker.benchmarkatoms import CheckerResult
from DikeBenchmarker.solveradaptors.abstractexecutable import AbstractExecutable

__all__ = ["CheckerAdaptor"]

_CHECKERS_DIR = importlib.resources.files("DikeBenchmarker.external.checkers")


def _checker_bin(name: str) -> str:
    """Return the absolute path to a bundled checker binary."""
    return str(_CHECKERS_DIR.joinpath(name))


class CheckerAdaptor(AbstractExecutable):
    """A class for executing checkers of sat or unsat certificates."""

    # Verified checkers whose maximum heap size is fixed at compile time ship as
    # separate 32 GB, 64 GB, and 256 GB binaries. A checker id may carry a
    # trailing "32", "64", or "256" to select one; without it the 32 GB build
    # is used.
    HEAP_VARIANTS = ("256", "64", "32")
    DEFAULT_VARIANT = "32"

    # Binaries that exist as per-variant builds. The selected size is appended to
    # the base name (e.g. "cake_lpr" -> "cake_lpr64").
    SCALABLE_BINARIES = ("cake_lpr", "cake_pb_cnf")

    # gratchk takes its heap limit as an MLton runtime argument instead of a
    # dedicated binary, so the matching value is patched into the command.
    # 256: sized to fit within the 239400 MiB checker_memory of all256.yml.
    GRAT_MAXHEAP = {"32": "31G", "64": "62G", "256": "230G"}

    def __init__(self, serialized: dict = None):
        """Initialize the CheckerAdaptor with a registry, or from a serialized dictionary if provided."""
        super().__init__(serialized)
        # drat-trim/dpr-trim have their own hard-coded internal time limit
        # (`-t`, default 40000s -- see their `--help`), independent of and
        # potentially BELOW whatever cpu-limit the checker-wrapper (e.g.
        # runsolver) enforces. Without an explicit `-t`, a slow-to-trim proof
        # can self-terminate with 's TIMEOUT' before the wrapper's own limit
        # fires (TIMEOUT=false/MEMOUT=false then look "correct" but are
        # misleading). Pass a value comfortably above any configured
        # checker-wrapper cpu-limit so that limit stays the sole authority.
        self.register(
            "drat",
            [_checker_bin("drat-trim"), _checker_bin("cake_lpr")],
            """
            $BIN0 $INST $CERT -t 90000 -C -D -L $CERT.trimmed 1> $TRIMMER_OUTPUT 2>&1
            $BIN1 $INST $CERT.trimmed 1> $CHECKER_OUTPUT 2>&1
            rc=$?
            rm -f $CERT.trimmed
            exit $rc
            """,
            None,
        )
        self.register(
            "dratbin",
            [_checker_bin("drat-trim"), _checker_bin("cake_lpr")],
            """
            $BIN0 $INST $CERT -t 90000 -i -C -D -L $CERT.trimmed 1> $TRIMMER_OUTPUT 2>&1
            $BIN1 $INST $CERT.trimmed 1> $CHECKER_OUTPUT 2>&1
            rc=$?
            rm -f $CERT.trimmed
            exit $rc
            """,
            None,
        )
        self.register(
            "dpr",
            [_checker_bin("dpr-trim"), _checker_bin("cake_lpr")],
            """
            $BIN0 $INST $CERT -t 90000 -C -D -L $CERT.trimmed 1> $TRIMMER_OUTPUT 2>&1
            $BIN1 $INST $CERT.trimmed 1> $CHECKER_OUTPUT 2>&1
            rc=$?
            rm -f $CERT.trimmed
            exit $rc
            """,
            None,
        )
        self.register(
            "dprbin",
            [_checker_bin("dpr-trim"), _checker_bin("cake_lpr")],
            """
            $BIN0 $INST $CERT -t 90000 -i -C -D -L $CERT.trimmed 1> $TRIMMER_OUTPUT 2>&1
            $BIN1 $INST $CERT.trimmed 1> $CHECKER_OUTPUT 2>&1
            rc=$?
            rm -f $CERT.trimmed
            exit $rc
            """,
            None,
        )
        self.register(
            "grat",
            [_checker_bin("gratgen"), _checker_bin("gratchk")],
            """
            $BIN0 $INST $CERT -o $CERT.gratp -l $CERT.gratl 1> $TRIMMER_OUTPUT 2>&1
            rm -f $CERT
            $BIN1 @MLton max-heap $MAXHEAP -- unsat $INST $CERT.gratl $CERT.gratp 1> $CHECKER_OUTPUT 2>&1
            rc=$?
            rm -f $CERT.gratl $CERT.gratp
            exit $rc
            """,
            None,
        )
        self.register(
            "gratbin",
            [_checker_bin("gratgen"), _checker_bin("gratchk")],
            """
            $BIN0 $INST $CERT -o $CERT.gratp -l $CERT.gratl -b 1> $TRIMMER_OUTPUT 2>&1
            rm -f $CERT
            $BIN1 @MLton max-heap $MAXHEAP -- unsat $INST $CERT.gratl $CERT.gratp 1> $CHECKER_OUTPUT 2>&1
            rc=$?
            rm -f $CERT.gratl $CERT.gratp
            exit $rc
            """,
            None,
        )
        self.register(
            "veripb",
            [_checker_bin("veripb"), _checker_bin("cake_pb_cnf")],
            """
            $BIN0 --cnf -u --elaborate $CERT.trimmed $INST $CERT 1> $TRIMMER_OUTPUT 2>&1
            rm -f $CERT
            $BIN1 $INST $CERT.trimmed 1> $CHECKER_OUTPUT 2>&1
            rc=$?
            rm -f $CERT.trimmed
            exit $rc
            """,
            None,
        )
        self.register(
            "sr",
            [_checker_bin("dsr-trim"), _checker_bin("lsr-check")],
            """
            $BIN0 $INST $CERT $CERT.trimmed 1> $TRIMMER_OUTPUT 2>&1
            $BIN1 $INST $CERT.trimmed 1> $CHECKER_OUTPUT 2>&1
            rc=$?
            rm -f $CERT.trimmed
            exit $rc
            """,
            None,
        )
        self.register(
            # Forward/streaming variant of "sr": dsr-trim defaults to backwards
            # checking with eager parsing, which loads the whole DSR proof into
            # memory and can exhaust RAM (xrealloc failure) even on small
            # formulas with large binary SR proofs. "-f" switches dsr-trim to
            # forwards checking with a streaming parser (one witness at a time),
            # keeping memory bounded at the cost of a larger, untrimmed LSR.
            "srfwd",
            [_checker_bin("dsr-trim"), _checker_bin("lsr-check")],
            """
            $BIN0 -f $INST $CERT $CERT.trimmed 1> $TRIMMER_OUTPUT 2>&1
            $BIN1 $INST $CERT.trimmed 1> $CHECKER_OUTPUT 2>&1
            rc=$?
            rm -f $CERT.trimmed
            exit $rc
            """,
            None,
        )
        self.register(
            "none",
            [],
            "",
            None,
        )
        self.register(
            "satchecker",
            [_checker_bin("gratchk")],
            """
            grep "^v" $CERT | sed -re 's/^v//g' | awk '{sub(/ 0$/, ""); if (NR>1) print prev; prev=$0} END {if (NR>0) print prev " 0"}' > $TRIMMER_OUTPUT
            $BIN0 sat $INST $TRIMMER_OUTPUT 1> $CHECKER_OUTPUT 2>&1
            """,
            None,
        )

    def _split_variant(self, xid: str) -> tuple[str, str]:
        """Split a checker id into its base id and heap-size variant.

        A trailing "32" or "64" selects the heap-size variant of the checker;
        when absent the variant defaults to DEFAULT_VARIANT. The number is
        stripped only when the remainder is a registered checker, so ids such as
        "drat" or "none" are returned unchanged.
        """
        for variant in self.HEAP_VARIANTS:
            if xid.endswith(variant):
                base = xid[: -len(variant)]
                if base in self.registry:
                    return base, variant
        return xid, self.DEFAULT_VARIANT

    def _apply_variant_to_binaries(self, binaries: list[str], variant: str) -> list[str]:
        """Append the heap-size suffix to checker binaries that have per-variant builds."""
        return [b + variant if os.path.basename(b) in self.SCALABLE_BINARIES else b for b in binaries]

    def get_binaries(self, xid: str) -> list[str]:
        """Return the binary paths for a checker id, resolving its heap-size variant."""
        base_id, variant = self._split_variant(xid)
        return self._apply_variant_to_binaries(super().get_binaries(base_id), variant)

    def format_command(self, xid, binaries, instance: str, certificate: str, trimmer_output: str, checker_output: str) -> str:
        """Get the command line for a given checker ID, replacing placeholders."""
        base_id, variant = self._split_variant(xid)
        result = self._format_base(base_id, binaries)
        result = result.replace("$MAXHEAP", self.GRAT_MAXHEAP[variant])
        result = self._format_extra(result, instance, certificate, trimmer_output, checker_output)
        return result

    def _format_extra(self, base: str, instance: str, certificate: str, trimmer_output: str, checker_output: str) -> str:
        """Get the command line for a given checker ID, replacing placeholders."""
        return (
            base.replace("$INST", instance).replace("$CERT", certificate).replace("$TRIMMER_OUTPUT", trimmer_output).replace("$CHECKER_OUTPUT", checker_output)
        )

    def parse_result(self, trimmer_file: str, checker_file: str) -> CheckerResult:
        """Classify the trimmer + checker pipeline."""
        if not os.path.exists(trimmer_file):
            return CheckerResult(CheckerResult.State.ERROR, "no trimmer output")

        trimmer_verdict = None
        with open(trimmer_file, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped.startswith("s "):
                    trimmer_verdict = stripped[2:].strip()
                elif "Ran out of memory" in line:
                    trimmer_verdict = "MEMOUT"

        # non-VERIFIED trimmer outcomes never yield a checker verdict
        trimmer_failure_detail = {
            None: "trimmer no verdict",
            "MEMOUT": "trimmer internal memout",
            "TIMEOUT": "trimmer internal timeout",
            "ERROR": "trimmer error",
        }
        if trimmer_verdict in trimmer_failure_detail:
            return CheckerResult(CheckerResult.State.ERROR, trimmer_failure_detail[trimmer_verdict])

        if not os.path.exists(checker_file):
            return CheckerResult(CheckerResult.State.ERROR, f"trimmer {trimmer_verdict}, no checker output")

        with open(checker_file, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped.startswith("s "):
                    verdict = stripped[2:].strip()
                    if verdict.startswith("VERIFIED"):
                        return CheckerResult(CheckerResult.State.VERIFIED, None)
                    return CheckerResult(CheckerResult.State.UNVERIFIED, f"trimmer {trimmer_verdict}, checker {verdict}")

        return CheckerResult(CheckerResult.State.UNKNOWN, f"trimmer {trimmer_verdict}, no checker verdict")
