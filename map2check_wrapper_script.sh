#!/bin/bash

# Map2Check wrapper script to SVCOMP


# Path to the Map2Check program
path_to_map2check=/home/nhb/Documents/ON_DEV/MAP2CHECK_FORTES_ON_DEV/ON_GIT_HUB/Map2Check-Fortes/map2check-fortes.py

# Command line, common to all tests.
# Run Map2Check 3 times. Each program in the category is executed 3 times,
# because of the nondeterministic model in the programs. It is important
# to note that from these 3 executions, we always consider the execution classified as
# FAILED (if any), i.e., an execution that the tool has identified a property violation.

# With this option, the tool drops all output into a temporary file that
# is identified in its output
map2check_options="--complete-check 3"



while getopts "c:mh" arg; do
    case $arg in
        h)
            echo "Usage: $0 [options] path_to_benchmark
Options:
-h             Print this message
-c propfile    Specifythe given property file"
            ;;
        c)
            # Given the lack of variation in the property file... we don't
            # actually interpret it. Instead we have the same options to all
            # tests (except for the memory checking ones), and define all the
            # error labels from other directories to be ERROR.
            ;;
    esac
done

# Store the path to the file we're going to be checking.
benchmark=$1

if test "${benchmark}" = ""; then
    echo "No benchmark given" >&2
    exit 1
fi

# The complete command to be executed
run_cmdline="${path_to_map2check} ${map2check_options} ${benchmark};"

# Invoke our command, wrapped in a timeout so that we can
# postprocess the results. `timeout` is part of coreutils on debian and fedora.
result_check=`timeout 895 bash -c "$run_cmdline"`

# Postprocessing: first, collect some facts
failed=`echo ${result_check} | grep -c "VERIFICATION FAILED"`
success=`echo ${result_check} | grep -c "VERIFICATION SUCCESSFUL"`

# Decide which result we determined here. The ordering is important: check for
# a counterexample first. The output file may contain both success and failure,
# this because we consider 3 executions of the verification. But if there's a
# trace, then there's an error.
if [ $failed -gt 0 ]; then
    # Error path found
    echo "FALSE"
    # Get trace log path
    trace_path=`echo ${result_check} | grep -o "<.*>" | sed -e s/'[\<\>]'//g`
    echo "The trace log is in ${trace_path}"
elif [ $success -gt 0 ]; then
    echo "TRUE"
else
    echo "UNKNOWN"
    # Clean up after ourselves. This because, how the Map2Check was interruped than
    # it is possible to have some left over temporary file
    # Get path from benchmark and then removing temporary files
    srcbench="$(dirname ${benchmark})"
    scripttmp="${srcbench}/build_2_check.sh"
    programtmp=`echo ${benchmark} | sed -e s/'.c'/'__mcf_new.c'/`

    if [ -f ${scripttmp} ]; then
        echo "REMOVE"
        rm ${scripttmp}
        rm "${srcbench}/check_safety_memory_FORTES.h"
        rm "${srcbench}/check_safety_memory_FORTES.o"
        rm ${programtmp}
        rm "*._mcf2check"
    fi
fi