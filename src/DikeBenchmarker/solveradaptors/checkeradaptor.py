"""This module provides an adaptor for executing checkers of sat or unsat certificates."""

import os

from DikeBenchmarker.solveradaptors.abstractexecutable import AbstractExecutable

__all__ = ["CheckerAdaptor"]


class CheckerAdaptor(AbstractExecutable):
    """A class for executing checkers of sat or unsat certificates."""

    # Verified checkers whose maximum heap size is fixed at compile time ship as
    # separate 32 GB and 64 GB binaries. A checker id may carry a trailing "32"
    # or "64" to select one; without it the 32 GB build is used.
    HEAP_VARIANTS = ("32", "64")
    DEFAULT_VARIANT = "32"

    # Binaries that exist as per-variant builds. The selected size is appended to
    # the base name (e.g. "cake_lpr" -> "cake_lpr64").
    SCALABLE_BINARIES = ("cake_lpr", "cake_pb_cnf")

    # gratchk takes its heap limit as an MLton runtime argument instead of a
    # dedicated binary, so the matching value is patched into the command.
    GRAT_MAXHEAP = {"32": "31G", "64": "62G"}

    def __init__(self, serialized: dict = None):
        """Initialize the CheckerAdaptor with a registry, or from a serialized dictionary if provided."""
        super().__init__(serialized)
        self.register(
            "drat",
            ["./external/checkers/drat-trim", "./external/checkers/cake_lpr"],
            """
            $BIN0 $INST $CERT -C -D -L $CERT.trimmed 1> $TRIMMER_OUTPUT 2>&1
            $BIN1 $INST $CERT.trimmed 1> $CHECKER_OUTPUT 2>&1
            rc=$?
            rm -f $CERT.trimmed
            exit $rc
            """,
            None,
        )
        self.register(
            "dratbin",
            ["./external/checkers/drat-trim", "./external/checkers/cake_lpr"],
            """
            $BIN0 $INST $CERT -i -C -D -L $CERT.trimmed 1> $TRIMMER_OUTPUT 2>&1
            $BIN1 $INST $CERT.trimmed 1> $CHECKER_OUTPUT 2>&1
            rc=$?
            rm -f $CERT.trimmed
            exit $rc
            """,
            None,
        )
        self.register(
            "dpr",
            ["./external/checkers/dpr-trim", "./external/checkers/cake_lpr"],
            """
            $BIN0 $INST $CERT -C -D -L $CERT.trimmed 1> $TRIMMER_OUTPUT 2>&1
            $BIN1 $INST $CERT.trimmed 1> $CHECKER_OUTPUT 2>&1
            rc=$?
            rm -f $CERT.trimmed
            exit $rc
            """,
            None,
        )
        self.register(
            "dprbin",
            ["./external/checkers/dpr-trim", "./external/checkers/cake_lpr"],
            """
            $BIN0 $INST $CERT -i -C -D -L $CERT.trimmed 1> $TRIMMER_OUTPUT 2>&1
            $BIN1 $INST $CERT.trimmed 1> $CHECKER_OUTPUT 2>&1
            rc=$?
            rm -f $CERT.trimmed
            exit $rc
            """,
            None,
        )
        self.register(
            "grat",
            ["./external/checkers/gratgen", "./external/checkers/gratchk"],
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
            ["./external/checkers/gratgen", "./external/checkers/gratchk"],
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
            ["./external/checkers/veripb", "./external/checkers/cake_pb_cnf"],
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
            ["./external/checkers/dsr-trim", "./external/checkers/lsr-check"],
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
            "none",
            [],
            "",
            None,
        )
        self.register(
            "satchecker",
            ["./external/checkers/gratchk"],
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

    def parse_result(self, outfile: str):
        """Extract the result from the checker file."""
        with open(outfile, "r", encoding="utf-8") as f:
            for line in f:
                if "VERIFIED" in line:
                    return line
        return "UNKNOWN"
