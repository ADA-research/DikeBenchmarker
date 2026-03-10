"""This module provides an adaptor for executing checkers of sat or unsat certificates."""

from DikeBenchmarker.solveradaptors.abstractexecutable import AbstractExecutable

__all__ = ["CheckerAdaptor"]


class CheckerAdaptor(AbstractExecutable):
    """A class for executing checkers of sat or unsat certificates."""

    def __init__(self, serialized: dict = None):
        """Initialize the CheckerAdaptor with a registry, or from a serialized dictionary if provided."""
        super().__init__(serialized)
        self.register(
            "drat",
            ["./external/checkers/drat-trim", "./external/checkers/cake_lpr"],
            """
            $BIN0 $INST $CERT -C -D -L $CERT.trimmed 1> $TRIMMER_OUTPUT 2>&1
            $BIN1 $INST $CERT.trimmed 1> $CHECKER_OUTPUT 2>&1
            rm -f $CERT.trimmed
            """,
            None,
        )
        self.register(
            "dratbin",
            ["./external/checkers/drat-trim", "./external/checkers/cake_lpr"],
            """
            $BIN0 $INST $CERT -i -C -D -L $CERT.trimmed 1> $TRIMMER_OUTPUT 2>&1
            $BIN1 $INST $CERT.trimmed 1> $CHECKER_OUTPUT 2>&1
            rm -f $CERT.trimmed
            """,
            None,
        )
        self.register(
            "dpr",
            ["./external/checkers/dpr-trim", "./external/checkers/cake_lpr"],
            """
            $BIN0 $INST $CERT -C -D -L $CERT.trimmed 1> $TRIMMER_OUTPUT 2>&1
            $BIN1 $INST $CERT.trimmed 1> $CHECKER_OUTPUT 2>&1
            rm -f $CERT.trimmed
            """,
            None,
        )
        self.register(
            "dprbin",
            ["./external/checkers/dpr-trim", "./external/checkers/cake_lpr"],
            """
            $BIN0 $INST $CERT -i -C -D -L $CERT.trimmed 1> $TRIMMER_OUTPUT 2>&1
            $BIN1 $INST $CERT.trimmed 1> $CHECKER_OUTPUT 2>&1
            rm -f $CERT.trimmed
            """,
            None,
        )
        self.register(
            "grat",
            ["./external/checkers/gratgen", "./external/checkers/gratchk"],
            """
            $BIN0 $INST $CERT -o $CERT.gratp -l $CERT.gratl 1> $TRIMMER_OUTPUT 2>&1
            rm -f $CERT
            $BIN1 @MLton max-heap 30G -- unsat $INST $CERT.gratl $CERT.gratp 1> $CHECKER_OUTPUT 2>&1
            rm -f $CERT.gratl $CERT.gratp
            """,
            None,
        )
        self.register(
            "gratbin",
            ["./external/checkers/gratgen", "./external/checkers/gratchk"],
            """
            $BIN0 $INST $CERT -o $CERT.gratp -l $CERT.gratl -b 1> $TRIMMER_OUTPUT 2>&1
            rm -f $CERT
            $BIN1 @MLton max-heap 30G -- unsat $INST $CERT.gratl $CERT.gratp 1> $CHECKER_OUTPUT 2>&1
            rm -f $CERT.gratl $CERT.gratp
            """,
            None,
        )
        self.register(
            "veripb",
            ["./external/checkers/pboxide_veripb", "./external/checkers/cake_pb_cnf"],
            """
            $BIN0 --cnf --elaborate $CERT.trimmed $INST $CERT 1> $TRIMMER_OUTPUT 2>&1
            rm -f $CERT
            $BIN1 $INST $CERT.trimmed 1> $CHECKER_OUTPUT 2>&1
            rm -f $CERT.trimmed
            """,
            None,
        )
        self.register(
            "satchecker",
            ["./external/checkers/gratchk"],
            """
            grep "^v" $CERT | sed -re 's/^v//g' > $CERT.model
            $BIN0 sat $INST $CERT.model 1> $CHECKER_OUTPUT 2>&1
            rm -f $CERT.model
            """,
            None,
        )

    def format_command(self, xid, binaries, instance: str, certificate: str, trimmer_output: str, checker_output: str) -> str:
        """Get the command line for a given checker ID, replacing placeholders."""
        result = self._format_base(xid, binaries)
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
