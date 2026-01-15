#!/bin/bash
start=$(date +%s)

solver=$1
checker=$2
bench=$3
# bench=${@: -2}
# checker=${@: -1}
# args=${@:2:$#-2}

prefix=$(basename "$bench" | cut -d'-' -f1)

results="./tmpresults"

mkdir -p $results

sroot="./solvers/"
croot="./checkers/"
exec="../benchexec/bin/runexec --timelimit 5000s --memlimit 30GB --output $results/output.log --no-tmpfs --result-files proof.out --output-directory . --overlay-dir ../.. --read-only-dir / --debug"

echo $exec $solver $bench $results
$exec $solver $bench $results 1> $results/solver.out
echo "Solver done. Runexec exit code: $?"
ls -hal 
ls -hal $results

if ( grep "s SATISFIABLE" $results/output.log > /dev/null ); then
    rm -f proof.out
    echo "s SATISFIABLE"
    grep "^v" $results/output.log | sed -re 's/^v//g' > $results/model.out
    $croot/gratchk sat $bench $results/model.out  1> $results/mcheck.out  2> $results/mcheck.err
    grep "^s" $results/mcheck.out
elif ( grep "s UNSATISFIABLE" $results/output.log > /dev/null ); then
    echo "s UNSATISFIABLE"
    case $checker in
        drat)
            $croot/drat-trim $bench proof.out -C -D -L proof.lrat  1> $results/trimmer.out  2> $results/trimmer.err
            $croot/cake_lpr $bench proof.lrat  1> $results/checker.out  2> $results/checker.err
            rm -f proof.lrat
            ;;
        dratbin)
            $croot/drat-trim $bench proof.out -i -C -D -L proof.lrat  1> $results/trimmer.out  2> $results/trimmer.err
            $croot/cake_lpr $bench proof.lrat  1> $results/checker.out  2> $results/checker.err
            rm -f proof.lrat
            ;;
        dpr)
            $croot/dpr-trim $bench proof.out -C -D -L proof.lrat  1> $results/trimmer.out  2> $results/trimmer.err
            $croot/cake_lpr $bench proof.lrat  1> $results/checker.out  2> $results/checker.err
            rm -f proof.lrat
            ;;
        dprbin)
            $croot/dpr-trim $bench proof.out -i -C -D -L proof.lrat  1> $results/trimmer.out  2> $results/trimmer.err
            $croot/cake_lpr $bench proof.lrat  1> $results/checker.out  2> $results/checker.err
            rm -f proof.lrat
            ;;
        grat)
            $croot/gratgen $bench proof.out -o proof.gratp -l proof.gratl  1> $results/trimmer.out  2> $results/trimmer.err 
            rm -f $results/proof.out
            $croot/gratchk @MLton max-heap 30G -- unsat $bench proof.gratl proof.gratp  1> $results/checker.out  2> $results/checker.err
            rm -f proof.gratl proof.gratp
            ;;
        gratbin)
            $croot/gratgen $bench proof.out -o proof.gratp -l proof.gratl -b  1> $results/trimmer.out  2> $results/trimmer.err
            rm -f $results/proof.out
            $croot/gratchk @MLton max-heap 30G -- unsat $bench proof.gratl proof.gratp  1> $results/checker.out  2> $results/checker.err
            rm -f proof.gratl proof.gratp
            ;;
        veripb)
            # source $croot/veripb/bin/activate
            # veripb --no-checkDeletion --cnf --proofOutput proof.cakepb $bench proof.out  1> $results/trimmer.out  2> $results/trimmer.err
            $croot/pboxide_veripb --cnf --elaborate proof.cakepb $bench proof.out  1> $results/trimmer.out  2> $results/trimmer.err
            rm -f proof.out
            $croot/cake_pb_cnf $bench proof.cakepb  1> $results/checker.out  2> $results/checker.err
            rm -f proof.cakepb
            # deactivate
            ;;
        *)
            echo "Unknown checker: $checker"
            exit 1
            ;;
    esac
    grep "^s" $results/checker.out
fi

end=$(date +%s)
echo "Total wallclock time: $((end - start)) seconds"
