#!/usr/bin/env python
# -*- coding: latin1 -*-

from __future__ import print_function

import argparse
import sys
import os
import commands
import re
import csv
import ConfigParser
import shutil
import time
from pipes import quote
import subprocess, datetime, os, time, signal


# DEPENDENCY PARAMETERS
ABS_PATH_FILE = os.path.dirname(os.path.abspath(__file__))
PATH_FILE_SETTINGS = ABS_PATH_FILE+'/settings.cfg'
if not os.path.isfile(PATH_FILE_SETTINGS):
    print('Error: unable to find the settings.cfg file')
    print('Please run ./configure to check the prerequisites to use Map2Check-FORTES tool')
    sys.exit()

config = ConfigParser.ConfigParser()
config.read(PATH_FILE_SETTINGS)
check_status_path = config.get('MAPFORTES_TOOL', 'mapfortes_path', 0)
if check_status_path == 'empty' :
    print("Sorry, you need to set up the Map2Check-FORTES path in settings.cfg file. See REAME file.")
    sys.exit()


# Name of the final report
OUTPUT_REPORT_FILE = check_status_path+"/<name_>report.html"
# Name of the tmp report that is generated according to tests execution
TMP_REPORT_FILE = check_status_path+'/tmp_result.html'


PATH_MAP_2_CHECK_FORTES = check_status_path+'/map2check.py'
if not os.path.isfile(PATH_MAP_2_CHECK_FORTES):
    print('Error: unable to find the map2check.py file')
    sys.exit()


# HTML Model Report
PATH_HTML_MODEL_REPORT = check_status_path+'/modules/html_report/report_model.html'
if not os.path.isfile(PATH_HTML_MODEL_REPORT):
    print('Error: unable to find the report_model.html file')
    sys.exit()

# API library location
PATH_API_LIBRARY = check_status_path+'/modules/map2check/library/'
if not os.path.isdir(PATH_API_LIBRARY):
    print('Error: unable to find the path to API library')
    sys.exit()

list_to_write_in_html = []
list_csv_generation = []
id_count = 1
list_delete_tmp_file = []



# CPAChecker
CPACHECKER_PATH = '/home/nhb/Documents/ON_DEV/CPAChecker/trunk/'
CPACHECKER_OPTIONS = 'scripts/cpa.sh -preprocess -sv-comp14--memorysafety -spec config/specification/cpalien-leaks.spc ' \
                     '-spec config/specification/TerminatingFunctions.spc -setprop cfa.useMultiEdges=false ' \
                     '-setprop parser.transformTokensToLines=true -spec'


# Number of time that the analyzed program will be executed to perform the analysis
NUMEBER_OF_RE_EXEC_EXP = 3

# Variables to memory usage
ACTUAL_MEM_USED_EXEC_inMB = 0.0
ACTUAL_TC_GEN_inMB = 0.0
TOTAL_TC_GEN_inMB = 0.0
ACTUAL_TIME_TC_GEN = 0
TOTAL_TIME_TC_GEN = 0
ACTUAL_GEN_GRAPH_inMB = 0.0
TOTAL_GEN_GRAPH_inMB = 0.0
ACTUAL_TIME_GEN_GRAPH = 0.0
TOTAL_TIME_GEN_GRAPH = 0.0


def get_mem_usage(_listtxtoutput):
    global ACTUAL_MEM_USED_EXEC_inMB
    #txt_result = _listtxtoutput.split("\n")

    ru_maxrss = float(_listtxtoutput[-1].strip())
    ACTUAL_MEM_USED_EXEC_inMB = ru_maxrss * float(0.0009765625)


tmp_FINAL_TIME = 0

ACTUAL_FILE_PATH = ''

def timeout_command(command, timeout):

    global tmp_FINAL_TIME

    if os.path.exists("/tmp/trace_of_program_exec_map2check.tmp"):
        os.remove("/tmp/trace_of_program_exec_map2check.tmp")
    else:
        trace_file = open("/tmp/trace_of_program_exec_map2check.tmp","w")
        trace_file.write("-----------------------------------------------------------------------\n")
        trace_file.write(">>> Trace of "+str(ACTUAL_FILE_PATH)+"\n")
        trace_file.write(">>> Generated at "+str(datetime.datetime.now())+"\n")
        trace_file.write("\n")
        trace_file.close()

    # generating the cammad to be executed
    cmd_shell = "time -f %M timeout " + str(timeout) + " " + command + " >> /tmp/trace_of_program_exec_map2check.tmp"

    start_t = time.time()
    result_only_stderr = commands.getoutput(cmd_shell)
    end_t = time.time()

    # for my details
    tmp_FINAL_TIME = time.time()

    tt = end_t - start_t
    list_out_exec = []


    # generating data to report
    # output str to list
    result_stdrr_list = result_only_stderr.split("\n")
    len_stderr_list = len(result_stdrr_list)
    # get memory
    result_only_mem = result_stdrr_list[len_stderr_list-1]
    del result_stdrr_list[len_stderr_list-1]
    # removing possible timeout msg
    for index, line in enumerate(result_stdrr_list):
        match_to = re.search("timeout: the monitored command dumped core", line)
        if match_to:
            del result_stdrr_list[index]
            break
    # generating stdout list
    result_sdtout = commands.getoutput("tail -n 20 /tmp/trace_of_program_exec_map2check.tmp")
    result_sdtout_list = result_sdtout.split("\n")


    #os.remove("/tmp/trace_of_program_exec_map2check.tmp")


    if tt > timeout:
        return ["TIME OUT",result_only_mem,result_stdrr_list,result_sdtout_list]
    else:
        # Get the needed lines from file
        return ["EXECUTED",result_only_mem,result_stdrr_list,result_sdtout_list]





def set_codes_to_experiment(pathCPrograms):
    
    global list_csv_generation
    global id_count
    global OUTPUT_REPORT_FILE
    global ACTUAL_MEM_USED_EXEC_inMB
    global tmp_FINAL_TIME
    global list_delete_tmp_file
    global ACTUAL_GEN_GRAPH_inMB
    global ACTUAL_TIME_GEN_GRAPH
    global ACTUAL_FILE_PATH
    
        
    # Map2Check PARAMS
    MAP2CHECK_EXECUTABLE = "map2check.py"
    MAP2CHECK_VERSION = commands.getoutput(PATH_MAP_2_CHECK_FORTES+" -v")
    MAP2CHECK_PARAMS="map2check.py file.c"
    
    # SYSTEM INFO
    DATE_EXECUTION = commands.getoutput("date")    
    CPU_CORE_NUMBER = commands.getoutput("cat /proc/cpuinfo | grep processor | wc -l")
    OS = commands.getoutput("uname -sr")
    CPU_INFO = "CPU:"+commands.getoutput("cat /proc/cpuinfo | grep \"model name\" | tail -n1 | cut -d \":\" -f2")
    MEM_INFO = "RAM:"+commands.getoutput("cat /proc/meminfo | grep \"MemTotal\" | cut -d \":\" -f2").strip()
    LIMIT_EXP = "timelimit: 900 s, memlimit: 5120 MB, CPU core limit: 8"
    INITIAL_TIMESTAMP = time.time()

    OUTPUT_REPORT_FILE = OUTPUT_REPORT_FILE.replace("<name_>",str(os.path.basename(pathCPrograms))+"_")

    #print(DATE_EXECUTION)
    #print(INITIAL_TIMESTAMP)
    #print(CPU_CORE_NUMBER)
    #print(CPU_INFO)
    #print(MEM_INFO)
    
    # HTML CONTENT
    HTML_TABLE_HEADER = "<thead> \n " \
                        "<tr id=\"tool\">" \
                          "<td style=\"width: 60%\">Tool</td>" \
                          "<td colspan=\"10\">"+MAP2CHECK_VERSION+"</td>" \
                        "</tr>"\
                        "<tr id=\"limits\">" \
                          "<td>Limits</td>" \
                          "<td colspan=\"10\">"+LIMIT_EXP+"</td>"+\
                        "</tr>" \
                        "<tr id=\"os\">" \
                          "<td>OS</td>" \
                          "<td colspan=\"10\">"+OS+"</td>"+\
                        "</tr>" \
                        "<tr id=\"system\">" \
                          "<td>System</td>" \
                          "<td colspan=\"10\">"+CPU_INFO+" - "+MEM_INFO+"</td>" \
                        "</tr>" \
                        "<tr id=\"date\">" \
                          "<td>Date of run</td>" \
                          "<td colspan=\"10\">"+DATE_EXECUTION+"</td>" \
                        "</tr>" \
                        "<tr id=\"options\">" \
                          "<td>Options</td>" \
                          "<td colspan=\"10\">"+MAP2CHECK_PARAMS+"</td>" \
                        "</tr>" \
                        "<tr id=\"columnTitles\">" \
                          "<td class=\"clickable\" "+"title=\"Click here to toggle visibility of columns\">"+str(pathCPrograms)+\
                          "</td>" \
                          "<td colspan=\"1\" class=\"clickable\" title=\"Click here to show a graph of this column\">" \
                          "status</td>" \
                          "<td colspan=\"1\" class=\"clickable\" title=\"Click here to show a graph of this column\">" \
                          "CPAChecker re-check status</td>" \
                          "<td colspan=\"1\" class=\"clickable\" title=\"Click here to show a graph of this column\">" \
                          "total time(s)</td>" \
                          "<td colspan=\"1\" class=\"clickable\" title=\"Click here to show a graph of this column\">" \
                          "total memory(MB)</td>" \
                          "<td colspan=\"1\" class=\"clickable\" title=\"Click here to show a graph of this column\">" \
                          "memory(MB) in EXEC</td>" \
                          "<td colspan=\"1\" class=\"clickable\" title=\"Click here to show a graph of this column\">" \
                          "time(s) Test Case Generation</td>" \
                          "<td colspan=\"1\" class=\"clickable\" title=\"Click here to show a graph of this column\">" \
                          "memory(MB) Test Case Generation</td>" \
                          "<td colspan=\"1\" class=\"clickable\" title=\"Click here to show a graph of this column\">" \
                          "GraphML Status</td>" \
                          "<td colspan=\"1\" class=\"clickable\" title=\"Click here to show a graph of this column\">" \
                          "time(s) GraphML Generation</td>" \
                          "<td colspan=\"1\" class=\"clickable\" title=\"Click here to show a graph of this column\">" \
                          "memory(MB) GraphML Generation</td>" \
                        "</tr>" \
                        "</thead> \n <tbody> \n"
    #print(HTML_TABLE_HEADER)
    #html_report.write(HTML_TABLE_HEADER)
    #list_to_write_in_html.append(HTML_TABLE_HEADER)
    html_tmp_report = open(TMP_REPORT_FILE, "a+b")
    html_tmp_report.write(HTML_TABLE_HEADER)                
    html_tmp_report.close()
    
    # REPORT CONTROL
    TOTAL_FILES         = 0
    TOTAL_MEM_IN_EXE    = 0
    CORRECT_RESULTS     = 0
    TOTAL_MEMO_CORRECT  = 0
    TIME_TOTAL_CORRECT  = 0
    TCEXCMB_TOTAL_CORRECT = 0
    CORRECT_TRUES       = 0
    CPACHECK_POSITIVE_cont   = 0
    CORRECT_FALSES      = 0
    CPACHECK_NEGATIVE_cont   = 0
    FALSE_POSITIVES     = 0
    TCEXCMB_TOTAL_FPOSITI = 0
    TOTAL_MEMO_FPOSITI  = 0
    TIME_TOTAL_FPOSITI  = 0
    FALSE_NEGATIVES     = 0
    TCEXCMB_TOTAL_FNEGATI = 0
    TIME_TOTAL_FNEGATI  = 0
    TOTAL_MEMO_FNEGATI  = 0
    NUM_UNKNOW_AND_TO   = 0
    MAX_SCORE           = 0
    TOTAL_POINTS        = 0
    COUNT_EXP_TRUE      = 0
    COUNT_EXP_FALSE     = 0

    STATUS_GRAPHML_GEN  = True
    
    #cp ./REPORT/header.html $OUTPUT_REPORT_FILE
    #echo $HTML_TABLE_HEADER >> $OUTPUT_REPORT_FILE
    
    print("*** Map2Check-Fortes Benchmark Runner (Single-Core) v0.1 ***")
    print( "Tool: "+MAP2CHECK_VERSION)
    print( "Date of run: "+str(commands.getoutput("date")))
    print( "System: "+CPU_INFO+" -- "+MEM_INFO)
    print( "Options: only the program")
    print( "Source: "+pathCPrograms)
    
        
    #--------------------------------------------------------
    # Read each program in the folder benchmarks and then
    # run the tool in two phases:
    #   (1) generate the new instance of the program with the tests cases
    #   (2) execute the new program instance generated in phase (1)
    #--------------------------------------------------------

    # TODO: Mesure the mem for test case generation and the total with exec $$$$$$$$
    print()
    
    total_num_programs = 0
    
    # For internal log
    #header_csv_generation = "ID ; Program ; Status Generation ; Time" LOG_INT
    #list_csv_generation.append(header_csv_generation) LOG_INT
    
    # Get number total of the programs 
    for root, dirs, files in os.walk(pathCPrograms):                
        for file in files:
            if file.endswith(".c"):
                total_num_programs += 1
                
    TOTAL_FILES = total_num_programs
    
    
    for root, dirs, files in os.walk(pathCPrograms):                
        for file in files:
            if file.endswith(".c"):
                print(file, end=" -> ")
                print(" "+str(id_count)+" from "+str(total_num_programs))
                get_path_program = os.path.join(root, file)
                
                FILENAME = get_path_program

                CPACHECKER_STATUS = "-"
                CPACHECKER_OUTPUT_PATH = ''
                
                
                # Get the expected result from benchmark program
                #EXPECTED_FAILED_RESULT = commands.getoutput("echo "+file+" | grep 'false'| wc -l")  
                matchRe_FAILED = re.search(r'false-(.[^\.]*)', str(file))
                matchRe_UNSAFE = re.search(r'_unsafe', str(file))
                EXPECTED_FAILED_RESULT = False
                if matchRe_FAILED or matchRe_UNSAFE:
                    print(">> EXPECTED < FALSE > - label: "+matchRe_FAILED.group(1))
                    COUNT_EXP_FALSE += 1
                    EXPECTED_FAILED_RESULT = True
                    MAX_SCORE = MAX_SCORE + 1
                else:
                    print(">> EXPECTED < TRUE >")
                    COUNT_EXP_TRUE += 1
                    EXPECTED_FAILED_RESULT = False
                    MAX_SCORE = MAX_SCORE + 2
                    
                                              
                
                # >> Run (1) generate the new instance of the program with the tests cases
                print("(1) Generating test cases and new program instance")
                INITIAL_EXECUTION_TIMESTAMP = time.time()
                list_result_gen = only_generate_code(get_path_program)
                ACTUAL_FILE_PATH = get_path_program
                print("\t\t Time: "+str("%1.3f" % ACTUAL_TIME_TC_GEN)+" MEM: "+str("%1.2f" % ACTUAL_TC_GEN_inMB))
                
                # >> Run (2) execute the new program instance generated in phase (1)
                FAILED = False
                SUCCESS = False
                flag_TIME_OUT = False
                #print("[DEBUG] result generation is: "+str(list_result_gen[0]))                
                #print(list_result_gen)
                
                if list_result_gen[0]:
                    print("(2) Run new program instance")                     
                    
                    name_file_result = list_result_gen[1].replace("._mcf2check","._out")
                    CPACHECKER_OUTPUT_PATH = list_result_gen[1].replace("._mcf2check",".cpachecker_out")
                    #list_delete_tmp_file.append(name_file_result)
                    #print("File result exec: "+name_file_result+"\n")                                        
                    
                    #commands.getoutput("(./"+list_result_gen[1]+") &> "+name_file_result)
                    #cmd_bin_exec = './'+str(list_result_gen[1])
                    cmd_bin_exec = str(list_result_gen[1])
                    
                    count_exe = 1
                    FINAL_EXECUTION_TIMESTAMP = 0
                    check_exec_status_FAILED = False
                    tmp_last_FAILED = False
                    tmp_last_time_FAILED = 0
                    tmp_last_mem_used_FAILED = 0.0
                    while count_exe <= NUMEBER_OF_RE_EXEC_EXP and not check_exec_status_FAILED:
                        flag_TIME_OUT = False
                        print("\t Run "+str(count_exe))

                        #get_OUT_result_exec = timeout_command(cmd_bin_exec, 900)
                        # The return is a list with:
                        #       (1) the status of execution
                        #       (2) the memory consumed
                        #       (3) stderr output in list
                        #       (3) sdtout output in list
                        # ex: return ["EXECUTED",result_only_mem,result_stdrr_list,result_sdtout_list]
                        #get_OUT_result_exec = timeout_command(cmd_bin_exec, 900)
                        get_OUT_result_exec = timeout_command(cmd_bin_exec, 900)



                        FINAL_EXECUTION_TIMESTAMP = tmp_FINAL_TIME #from timeout function
                        print("\t\t Finished execution")

                        
                        # Check if has a TIME OUT
                        #print("DEBUG out exec: "+str(get_OUT_result_exec[0].readlines()))
                        if not(str(get_OUT_result_exec[0]) == 'TIME OUT'):

                            tmp_list_OUT_STDERR = get_OUT_result_exec[2]
                            tmp_list_OUT_STDOUT = get_OUT_result_exec[3]

                            get_mem_usage(get_OUT_result_exec[1])


                            #DEBUG
                            print("\t\t Time: %1.2f" % (FINAL_EXECUTION_TIMESTAMP - INITIAL_EXECUTION_TIMESTAMP))
                            print("\t\t Memo: %1.2f" % ACTUAL_MEM_USED_EXEC_inMB)
                            
                            # From this executions we ALWAYS save the failed execution
                            # Check in the result of the bin execution                                                                
                            matchSTDOUT_FAILED = re.search(r'(\[Failed\])', str(tmp_list_OUT_STDOUT))
                            matchSTDERR_FAILED = re.search(r'(\[Failed\])', str(tmp_list_OUT_STDERR))                                        
                                                        
                            
                            if matchSTDOUT_FAILED or matchSTDERR_FAILED:
                                check_exec_status_FAILED = True
                                tmp_last_FAILED = check_exec_status_FAILED
                                tmp_last_time_FAILED = FINAL_EXECUTION_TIMESTAMP
                                tmp_last_mem_used_FAILED = ACTUAL_MEM_USED_EXEC_inMB
                                
                            if tmp_last_FAILED:
                                check_exec_status_FAILED = True
                                FINAL_EXECUTION_TIMESTAMP = tmp_last_time_FAILED
                                ACTUAL_MEM_USED_EXEC_inMB = tmp_last_mem_used_FAILED
                            
                            #save the execution result
                            if check_exec_status_FAILED:
                                # This write the multiples execution
                                outputRun = open(str("/tmp/trace_of_program_exec_map2check.tmp"), "a+b")
                                # This save only one FAILED, always rewriting

                                # outputRun = open(str(name_file_result), "w")
                                # #outputRun.write(str(tmp_list_OUT_STDOUT))
                                # # for line in tmp_list_OUT_STDOUT:
                                # #     outputRun.write(str(line)+" \n")
                                # #outputRun.write(str(tmp_list_OUT_STDERR))
                                #
                                # # append the file generated in the execution
                                #
                                for line in tmp_list_OUT_STDERR:
                                    #print(line)
                                    outputRun.write(str(line)+" \n")

                                outputRun.close()

                                # Change the name and move the trace log
                                os.system("mv /tmp/trace_of_program_exec_map2check.tmp "+name_file_result)


                                # Call to generate the GraphML - preliminary test
                                #print(get_path_program, name_file_result)
                                result_gen_graphml = generate_graphml(get_path_program, name_file_result)



                                if result_gen_graphml[0]:
                                    STATUS_GRAPHML_GEN = "true"
                                    # Running CPAChecker to check witness
                                    # Open dir where is CPAChecker and then run the tool inside from directory
                                    #print(result_gen_graphml[1]+" <<<<<< ML")

                                    if CPACHECKER_PATH:
                                        print("\t\t >>> Runnning CPAChecker")
                                        cwd = os.getcwd()
                                        os.chdir(CPACHECKER_PATH)
                                        #print("CMD: "+CPACHECKER_OPTIONS+" "+result_gen_graphml[1]+" "+get_path_program)
                                        result_recheck = commands.getoutput(CPACHECKER_OPTIONS+" "+result_gen_graphml[1]+" "+get_path_program)
                                        #
                                        list_recheck = result_recheck.split("\n")
                                        flag_cpa = False
                                        for line in list_recheck:
                                            match_failed_CPA = re.search(r"Verification result: FALSE", line)
                                            match_nobug_CPA = re.search(r"Verification result: TRUE", line)
                                            if match_failed_CPA:
                                                print("\t\t\t CPAChecker --- POSITIVE")
                                                CPACHECKER_STATUS = "positive"
                                                CPACHECK_POSITIVE_cont += 1
                                                flag_cpa = True
                                                break
                                            elif match_nobug_CPA:
                                                print("\t\t\t CPAChecker --- NEGATIVE")
                                                CPACHECKER_STATUS = "negative"
                                                CPACHECK_NEGATIVE_cont += 1
                                                flag_cpa = True
                                                break


                                        if not flag_cpa:
                                            print("\t\t\t CPAChecker --- UNKNOWN")


                                        os.chdir(cwd)
                                        # Write cpachecker log
                                        commands.getoutput("echo \""+result_recheck+"\" > "+CPACHECKER_OUTPUT_PATH)
                                        #print(result_recheck)
                                else:
                                    STATUS_GRAPHML_GEN = "ERROR"
                                print("\t\t Time G: "+str("%1.3f" % ACTUAL_TIME_GEN_GRAPH)+" MEM G: "+str("%1.2f" % ACTUAL_GEN_GRAPH_inMB))

                                print("\t\t Finished the analisys of this execution")
                            
                        else:
                            # We have a TIME OUT
                            #print("unknow") 
                            flag_TIME_OUT = True                   
                            FAILED = False
                            SUCCESS = False
                            
                        
                        count_exe += 1
                        time.sleep(3) # Wait for 3 second to the next execution
                                        
                    
                    
                    if not flag_TIME_OUT:                    
                        #if int(check_exec_status_FAILED): 
                        if check_exec_status_FAILED: 
                            #print("[DEBUG]: FAILED")                                   
                            FAILED = True
                            SUCCESS = False
                        else:
                            #print("[DEBUG]: SUCCESS")
                            FAILED = False
                            SUCCESS = True
                    
                    
                    
                else:
                    #print("unknow")
                    #print("[DEBUG]: UNKNOW")
                    flag_TIME_OUT = False
                    FAILED = False
                    SUCCESS = False
                    FINAL_EXECUTION_TIMESTAMP = time.time()

                TIME = FINAL_EXECUTION_TIMESTAMP - INITIAL_EXECUTION_TIMESTAMP
                TOTAL_EXECUTION_TIME = TIME
                
                #print("DEBUG: EXP_FALSE: "+str(EXPECTED_FAILED_RESULT)+" - FAILED: "+str(FAILED)+" - SUCCESS: "+str(SUCCESS))
                
                CSS_CLASS   = ""
                RESULT_TEXT = ""
                
                #flag_TIME_OUT
                
                if not FAILED and not SUCCESS and flag_TIME_OUT:
                    CSS_CLASS         = "status error"
                    RESULT_TEXT       = "timeout"
                    NUM_UNKNOW_AND_TO += 1
                    TOTAL_MEM_IN_EXE  += ACTUAL_MEM_USED_EXEC_inMB
                    #echo $(echo -e"\033[0;33munknown\033[0m" | cut -d " " -f2) "in $TIME""s"
                    print(">> ACTUAL: TIMEOUT in "+str(TIME)+" s")
                    print("\t\t Memo: %1.2f" % ACTUAL_MEM_USED_EXEC_inMB)
                    
                if not FAILED and not SUCCESS and not flag_TIME_OUT:
                    CSS_CLASS         = "status unknown"
                    RESULT_TEXT       = "unknown"
                    NUM_UNKNOW_AND_TO += 1
                    TOTAL_MEM_IN_EXE  += ACTUAL_MEM_USED_EXEC_inMB
                    #echo $(echo -e"\033[0;33munknown\033[0m" | cut -d " " -f2) "in $TIME""s"
                    print(">> ACTUAL: UNKNOWN in "+str(TIME)+" s")
                    print("\t\t Memo: %1.2f" % ACTUAL_MEM_USED_EXEC_inMB)
                  
                elif EXPECTED_FAILED_RESULT and FAILED and not flag_TIME_OUT:
                    #CSS_CLASS         = "correctProperty"
                    CSS_CLASS         = "status correct false"
                    RESULT_TEXT       = "false(label)"
                    CORRECT_RESULTS   = CORRECT_RESULTS + 1
                    CORRECT_FALSES    = CORRECT_FALSES + 1
                    TOTAL_MEM_IN_EXE  += ACTUAL_MEM_USED_EXEC_inMB
                    TCEXCMB_TOTAL_CORRECT += ACTUAL_MEM_USED_EXEC_inMB + ACTUAL_TC_GEN_inMB
                    TOTAL_MEMO_CORRECT  += ACTUAL_MEM_USED_EXEC_inMB

                    TIME_TOTAL_CORRECT += TIME
                    #echo $(echo -e "\033[0;32mfalse(label)\033[0m" | cut -d " " -f2) "in $TIME""s"
                    print(">> ACTUAL: false(label) in "+str(TIME)+" s")
                    print("\t\t Memo: %1.2f" % ACTUAL_MEM_USED_EXEC_inMB)
                  
                elif EXPECTED_FAILED_RESULT and not FAILED and not flag_TIME_OUT:
                    #CSS_CLASS         = "wrongProperty"
                    CSS_CLASS         = "status wrong true"
                    RESULT_TEXT       = "true"
                    FALSE_POSITIVES   = FALSE_POSITIVES + 1
                    TOTAL_MEM_IN_EXE  += ACTUAL_MEM_USED_EXEC_inMB
                    TOTAL_MEMO_FPOSITI += ACTUAL_MEM_USED_EXEC_inMB
                    TCEXCMB_TOTAL_FPOSITI += ACTUAL_MEM_USED_EXEC_inMB + ACTUAL_TC_GEN_inMB
                    TIME_TOTAL_FPOSITI += TIME
                    #echo $(echo -e "\033[0;31mtrue\033[0m" | cut -d " " -f2) "in $TIME""s"
                    print(">> ACTUAL: true in "+str(TIME)+" s")
                    print("\t\t Memo: %1.2f" % ACTUAL_MEM_USED_EXEC_inMB)
                  
                elif not EXPECTED_FAILED_RESULT and FAILED and not flag_TIME_OUT:
                    #CSS_CLASS         = "wrongProperty"
                    CSS_CLASS         = "status wrong false"
                    RESULT_TEXT       = "false(label)"
                    FALSE_NEGATIVES   = FALSE_NEGATIVES + 1
                    TOTAL_MEM_IN_EXE  += ACTUAL_MEM_USED_EXEC_inMB
                    TOTAL_MEMO_FNEGATI += ACTUAL_MEM_USED_EXEC_inMB
                    TCEXCMB_TOTAL_FNEGATI += ACTUAL_MEM_USED_EXEC_inMB + ACTUAL_TC_GEN_inMB
                    TIME_TOTAL_FNEGATI += TIME
                    #echo $(echo -e "\033[0;31mfalse(label)\033[0m" | cut -d " " -f2) "in $TIME""s"
                    print(">> ACTUAL: false(label) in "+str(TIME)+" s")
                    print("\t\t Memo: %1.2f" % ACTUAL_MEM_USED_EXEC_inMB)
                  
                elif not EXPECTED_FAILED_RESULT and not FAILED and not flag_TIME_OUT:
                    #CSS_CLASS         = "correctProperty"
                    CSS_CLASS         = "status correct true"
                    RESULT_TEXT       = "true"
                    CORRECT_RESULTS   = CORRECT_RESULTS + 1
                    CORRECT_TRUES     = CORRECT_TRUES + 1
                    TOTAL_MEM_IN_EXE  += ACTUAL_MEM_USED_EXEC_inMB
                    TOTAL_MEMO_CORRECT  += ACTUAL_MEM_USED_EXEC_inMB
                    TCEXCMB_TOTAL_CORRECT += ACTUAL_MEM_USED_EXEC_inMB + ACTUAL_TC_GEN_inMB
                    TIME_TOTAL_CORRECT += TIME
                    #echo $(echo -e "\033[0;32mtrue\033[0m" | cut -d " " -f2) "in $TIME""s"
                    print(">> ACTUAL: true in "+str(TIME)+" s")
                    print("\t\t Memo: %1.2f" % ACTUAL_MEM_USED_EXEC_inMB)
                  

                HTML_ENTRY="\t <tr><td>"+FILENAME+"</td><td class=\""+CSS_CLASS+"\">"+RESULT_TEXT+"</td>" \
                           "<td class=\"unknownValue\">" + str(CPACHECKER_STATUS) + "&nbsp;</td>" \
                           "<td class=\"unknownValue\">" + str(("%1.2f" % TIME)) + "&nbsp;</td>" \
                           "<td class=\"unknownValue\">" + str(("%1.2f" % (ACTUAL_MEM_USED_EXEC_inMB+ACTUAL_TC_GEN_inMB))) + "&nbsp;</td>" \
                           "<td class=\"unknownValue\">" + str(("%1.2f" % ACTUAL_MEM_USED_EXEC_inMB)) + "&nbsp;</td>" \
                           "<td class=\"unknownValue\">" + str(("%1.3f" % ACTUAL_TIME_TC_GEN)) + "&nbsp;</td>" \
                           "<td class=\"unknownValue\">" + str(("%1.2f" % ACTUAL_TC_GEN_inMB)) + "&nbsp;</td>" \
                           "<td class=\"unknownValue\">" + str(STATUS_GRAPHML_GEN) + "&nbsp;</td>" \
                           "<td class=\"unknownValue\">" + str(("%1.3f" % ACTUAL_TIME_GEN_GRAPH)) + "&nbsp;</td>" \
                           "<td class=\"unknownValue\">" + str(("%1.2f" % ACTUAL_GEN_GRAPH_inMB)) + "&nbsp;</td>" \
                           "</tr> \n"
                #commands.getoutput("echo \""+HTML_ENTRY+"\" >> "+OUTPUT_REPORT_FILE)              
                #html_report.write(HTML_ENTRY)
                #
                
                # write in tmp file the results
                #list_to_write_in_html.append(HTML_ENTRY)
                html_tmp_report = open(TMP_REPORT_FILE, "a+b")
                html_tmp_report.write(HTML_ENTRY)                
                html_tmp_report.close()
                
                id_count += 1
                 
    # end
    print()
    print("------------------------------------------------------")
    print()
    
    FINAL_TIMESTAMP = time.time()
    
    # CALCULATE POINTS
    TOTAL_POINTS = (TOTAL_POINTS + 2 * CORRECT_TRUES)   
    print("CORRECT_TRUES  : ",str(CORRECT_TRUES)) 
    TOTAL_POINTS = (TOTAL_POINTS + CORRECT_FALSES)    
    print("CORRECT_FALSES : ",str(CORRECT_FALSES)) 
    TOTAL_POINTS = (TOTAL_POINTS - 8 * FALSE_POSITIVES)    
    print("FALSE_POSITIVES: ",str(FALSE_POSITIVES)) 
    TOTAL_POINTS = (TOTAL_POINTS - 4 * FALSE_NEGATIVES)    
    print("FALSE_NEGATIVES: ",str(FALSE_NEGATIVES)) 
    print("UNKNOW and TO  : ",str(NUM_UNKNOW_AND_TO))
    print()
    print("COUNT_EXP_FALSE: ",str(COUNT_EXP_FALSE))
    print("COUNT_EXP_TRUE: ",str(COUNT_EXP_TRUE))
    print()
    print("COUNT CPAChecker POS: ",str(CPACHECK_POSITIVE_cont))
    print("COUNT CPAChecker NEG: ",str(CPACHECK_NEGATIVE_cont))

#    TOTAL_EXECUTION_TIME = FINAL_TIMESTAMP - INITIAL_TIMESTAMP
    
    # HTML CONTENT
    HTML_TABLE_FOOTER="</tbody> \n <tfoot>" \
                      "<tr>" \
                        "<td>total files</td>" \
                        "<td>"+str(TOTAL_FILES)+"</td>" \
                        "<td>"+str(CPACHECK_POSITIVE_cont+CPACHECK_NEGATIVE_cont)+"</td>" \
                        "<td>"+str(("%1.2f" % TOTAL_EXECUTION_TIME))+"&nbsp;</td>" \
                        "<td>"+str(("%1.2f" % (TOTAL_MEM_IN_EXE + TOTAL_TC_GEN_inMB + TOTAL_GEN_GRAPH_inMB)))+"&nbsp;</td>" \
                        "<td>"+str(("%1.2f" % TOTAL_MEM_IN_EXE))+"&nbsp;</td> " \
                        "<td>"+str(("%1.3f" % TOTAL_TIME_TC_GEN))+"&nbsp;</td>" \
                        "<td>"+str(("%1.2f" % TOTAL_TC_GEN_inMB))+"&nbsp;</td>" \
                        "<td class=\"score\">"+str("-")+"&nbsp;</td>" \
                        "<td>"+str(("%1.3f" % TOTAL_TIME_GEN_GRAPH))+"&nbsp;</td>" \
                        "<td>"+str(("%1.2f" % TOTAL_GEN_GRAPH_inMB))+"&nbsp;</td>" \
                      "</tr>" \
                      "<tr>" \
                        "<td title=\"(no bug exists + result is SAFE) OR "+\
                        "(bug exists + result is UNSAFE) OR (property is violated + violation is found)\">correct results</td>" \
                        "<td>"+ str(CORRECT_RESULTS)+"</td>" \
                        "<td>"+ str(CPACHECK_POSITIVE_cont) +"</td>" \
                        "<td>"+str(("%1.2f" % TIME_TOTAL_CORRECT))+"</td>" \
                        "<td>"+str(("%1.2f" % TCEXCMB_TOTAL_CORRECT))+"</td>" \
                        "<td>"+str(("%1.2f" % TOTAL_MEMO_CORRECT))+"</td>" \
                        "<td class=\"score\">-</td>" \
                        "<td class=\"score\">-</td>" \
                        "<td class=\"score\">-</td>" \
                        "<td class=\"score\">-</td>" \
                        "<td class=\"score\">-</td>" \
                      "</tr>" \
                      "<tr>" \
                        "<td title=\"bug exists + result is SAFE\">false negatives</td>" \
                        "<td>"+ str(FALSE_NEGATIVES)+"</td>" \
                        "<td class=\"score\">-</td>" \
                        "<td>"+str(("%1.2f" % TCEXCMB_TOTAL_FNEGATI))+"</td>" \
                        "<td>"+str(("%1.2f" % TIME_TOTAL_FNEGATI))+"</td>" \
                        "<td>"+str(("%1.2f" % TOTAL_MEMO_FNEGATI))+"</td>" \
                        "<td class=\"score\">-</td>" \
                        "<td class=\"score\">-</td>" \
                        "<td class=\"score\">-</td>" \
                        "<td class=\"score\">-</td>" \
                        "<td class=\"score\">-</td>" \
                      "</tr>" \
                      "<tr>" \
                        "<td title=\"no bug exists + result is UNSAFE\">false positives"+"</td>" \
                        "<td>"+str(FALSE_POSITIVES)+"</td>" \
                        "<td class=\"score\">-</td>" \
                        "<td>"+str(("%1.2f" % TCEXCMB_TOTAL_FPOSITI))+"</td>" \
                        "<td>"+str(("%1.2f" % TIME_TOTAL_FPOSITI))+"</td>" \
                        "<td>"+str(("%1.2f" % TOTAL_MEMO_FPOSITI))+"</td>" \
                        "<td class=\"score\">-</td>" \
                        "<td class=\"score\">-</td>" \
                        "<td class=\"score\">-</td>" \
                        "<td class=\"score\">-</td>" \
                        "<td class=\"score\">-</td>" \
                      "</tr>" \
                      "<tr>" \
                        "<td title=\"17 safe files, 15 unsafe files\">score ("+\
                        str(TOTAL_FILES)+" files, max score: "+str(MAX_SCORE)+")</td>" \
                        "<td class=\"score\">"+str(TOTAL_POINTS)+"</td>" \
                        "<td class=\"score\">-</td>" \
                        "<td class=\"score\">-</td>" \
                        "<td class=\"score\">-</td>" \
                        "<td class=\"score\">-</td>" \
                        "<td class=\"score\">-</td>" \
                        "<td class=\"score\">-</td>" \
                        "<td class=\"score\">-</td>" \
                        "<td class=\"score\">-</td>" \
                        "<td class=\"score\">-</td>" \
                      "</tr>" \
                      "</tfoot> \n </table></center></body></html> \n"
   
    #html_report.write(HTML_TABLE_FOOTER)
    #list_to_write_in_html.append(HTML_TABLE_FOOTER)
    html_tmp_report = open(TMP_REPORT_FILE, "a+b")
    html_tmp_report.write(HTML_TABLE_FOOTER)                
    html_tmp_report.close()
    
    print()
    print("*** RESULTS *** ")
    print("Total Files: "+str(TOTAL_FILES)+" in "+str(TOTAL_EXECUTION_TIME)+" s")
    print("Total Memory (MB): "+str(("%1.2f" % TOTAL_MEM_IN_EXE)))
    print("Correct Results: "+str(CORRECT_RESULTS))
    print("False Negatives: "+str(FALSE_NEGATIVES))
    print("False Positives: "+str(FALSE_POSITIVES))
    print("Score ( "+str(TOTAL_FILES)+" files, max score: "+str(MAX_SCORE)+"): "+str(TOTAL_POINTS))

    #commands.getoutput("echo \""+HTML_TABLE_FOOTER+"\" >> "+OUTPUT_REPORT_FILE)
    print()
    try:
        model_report = open(PATH_HTML_MODEL_REPORT, "r")
        model_report_lines = model_report.readlines()
        model_report.close()        


        html_report = open(OUTPUT_REPORT_FILE, "w")
        for index, line in enumerate(model_report_lines):
            # line to insert the results
            if (index+1) == 1242:
                #for lineTable in list_to_write_in_html:
                html_report.write(open(TMP_REPORT_FILE,"rb").read())
            else:
                html_report.write(line)
                
        html_report.close()
        
        #os.remove(PATH_HTML_MODEL_REPORT)
        os.remove(TMP_REPORT_FILE)

        
    except IOError:
            print("Could not read file: report_model.html")
            sys.exit()

    
    print("Report file generated: "+OUTPUT_REPORT_FILE)
    remove_tmp_files(list_delete_tmp_file)
    
    

def generate_graphml(_cProgram, _map2checkoutput):

    global list_csv_generation
    global id_count
    global PATH_MAP_2_CHECK_FORTES
    global ACTUAL_GEN_GRAPH_inMB
    global TOTAL_GEN_GRAPH_inMB
    global ACTUAL_TIME_GEN_GRAPH
    global TOTAL_TIME_GEN_GRAPH
    global ACTUAL_MEM_USED_EXEC_inMB



    graphmlpath = _cProgram.replace(".c",".graphml")

    # Take time to test case generation
    cmd = [PATH_MAP_2_CHECK_FORTES, _cProgram, "--map2checkout-to-graphml", _map2checkoutput]

    #cmd = cmd.split(" ")
    tctimeinital = datetime.datetime.now()
    process = subprocess.Popen(['time', '-f', '%M'] + cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    tctimefinal = datetime.datetime.now()
    timetcgen = (tctimefinal - tctimeinital).seconds + (tctimefinal - tctimeinital).microseconds * 0.000001


    ACTUAL_TIME_GEN_GRAPH = timetcgen
    TOTAL_TIME_GEN_GRAPH += timetcgen

    #Save result in file
    #print(process.stdout.readlines())
    #writenewcode = open(graphmlpath, "w")
    pathgraphml = ''
    for line in process.stdout.readlines():
        match_filegrahml = re.search(r"The Map2Check output in GraphML format is in <(.*)>",line)
        #writenewcode.write(line)
        if match_filegrahml:
            pathgraphml = match_filegrahml.group(1)
    #writenewcode.close()

    #print(process.stderr.readlines())

    tmp_save_actual_exemb = ACTUAL_MEM_USED_EXEC_inMB

    get_mem_usage(process.stderr.readlines())
    ACTUAL_GEN_GRAPH_inMB = ACTUAL_MEM_USED_EXEC_inMB
    TOTAL_GEN_GRAPH_inMB += ACTUAL_GEN_GRAPH_inMB

    ACTUAL_MEM_USED_EXEC_inMB = tmp_save_actual_exemb
    #ACTUAL_MEM_USED_EXEC_inMB = 0.0
    #os.system(PATH_MAP_2_CHECK_FORTES+" "+cProgram+" > "+new_c_program_name)

    # Checking if the generation was okay
    matchpython_error = re.search(r"Traceback (most recent call last):", graphmlpath)
    if matchpython_error:
        return [False,'']
    else:
        return [True,pathgraphml]




def only_generate_code(cProgram):
    
    global list_csv_generation
    global id_count
    global PATH_MAP_2_CHECK_FORTES
    global ACTUAL_TC_GEN_inMB
    global ACTUAL_MEM_USED_EXEC_inMB
    global TOTAL_TC_GEN_inMB
    global ACTUAL_TIME_TC_GEN
    global TOTAL_TIME_TC_GEN
    
    result_this_step = [] # 1 True or False; 2 bin name file
       
    new_c_program_name = cProgram.replace(".c","__mcf_new.c")
    list_delete_tmp_file.append(new_c_program_name)
    
    # Take time to test case generation
    #cmd = [PATH_MAP_2_CHECK_FORTES+" "+cProgram+" > "+new_c_program_name]
    # Partial track
    cmd = [PATH_MAP_2_CHECK_FORTES, "--only-assert", cProgram]
    # Complete track
    #cmd = [PATH_MAP_2_CHECK_FORTES, "--track-all", "--only-assert", cProgram]
    #cmd = ["cat "+PATH_MAP_2_CHECK_FORTES]

    #cmd = cmd.split(" ")
    tctimeinital = datetime.datetime.now()
    process = subprocess.Popen(['time', '-f', '%M'] + cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    tctimefinal = datetime.datetime.now()
    timetcgen = (tctimefinal - tctimeinital).seconds + (tctimefinal - tctimeinital).microseconds * 0.000001


    ACTUAL_TIME_TC_GEN = timetcgen
    TOTAL_TIME_TC_GEN += timetcgen

    #Save result in file
    #print(process.stdout.readlines())
    writenewcode = open(new_c_program_name, "w")
    for line in process.stdout.readlines():
        writenewcode.write(line)
    writenewcode.close()

    #print(process.stderr.readlines())

    get_mem_usage(process.stderr.readlines())
    ACTUAL_TC_GEN_inMB = ACTUAL_MEM_USED_EXEC_inMB
    TOTAL_TC_GEN_inMB += ACTUAL_TC_GEN_inMB
    ACTUAL_MEM_USED_EXEC_inMB = 0.0
    #os.system(PATH_MAP_2_CHECK_FORTES+" "+cProgram+" > "+new_c_program_name)



    # Checking if the generation of the code was complete sucessful    
    get_result_compile = only_compile_code(new_c_program_name)
        
    bin_name_file = new_c_program_name.replace("__mcf_new.c","__mcf_new._mcf2check")

    
    if get_result_compile:

        list_delete_tmp_file.append(bin_name_file)

        result_this_step.append(True)
        result_this_step.append(bin_name_file)
    else:
        result_this_step.append(False)
        result_this_step.append(bin_name_file)
        
    return result_this_step
        
        


def only_compile_code(cProgram):
    COMPILE_SCRIPT = './build_2_check.sh'
    
    head, tail = os.path.split(cProgram)
    
    # Now change the directory
    os.chdir( head )
        
    #print(COMPILE_SCRIPT+" "+tail)
    get_result = commands.getoutput(COMPILE_SCRIPT+" "+tail)
    
    has_bin_file = False
    
    # Check if exist the bin file
    # First of all get the name bin file???
    tail = tail.replace(".c","._mcf2check")                   
    if os.path.isfile(tail):
        has_bin_file = True
    else:
        has_bin_file = False
    
    # Return directory
    os.chdir( ".." )
    
    #return get_result
    return has_bin_file


def copy_api_library(_dircprograms):
    global list_delete_tmp_file
    global PATH_API_LIBRARY

    #The script to compile
    pathscriptcompile = PATH_API_LIBRARY+'build_2_check.sh'
    pathheaderapi = PATH_API_LIBRARY+'check_safety_memory_FORTES.h'
    pathlibapi = PATH_API_LIBRARY+'check_safety_memory_FORTES.o'

    try:
        shutil.copy2(pathscriptcompile, _dircprograms)
        list_delete_tmp_file.append(_dircprograms+'/build_2_check.sh')

        shutil.copy2(pathheaderapi, _dircprograms)
        list_delete_tmp_file.append(_dircprograms+'/check_safety_memory_FORTES.h')

        shutil.copy2(pathlibapi, _dircprograms)
        list_delete_tmp_file.append(_dircprograms+'/check_safety_memory_FORTES.o')

    except shutil.Error as e:
        print('Error: %s' % e)
        raise
        # eg. source or destination doesn't exist
    except IOError as e:
        print('Error: %s' % e.strerror)
        raise


def remove_tmp_files(list_path):
    #return True
    for path in list_path:
        os.remove(path)





# -------------------------------------------------
# Main python program
# -------------------------------------------------

if __name__ == "__main__": 
    
    ############# Parse args options
    parser = argparse.ArgumentParser(description='Run experiment using Map2Check-FORTES v3')
    parser.add_argument(dest='dirCPrograms', metavar='program_directory', type=str, 
               help='the C program directory to be analyzed')    
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-g','--only-generated-code', action="store_true" , dest='setOnlyCode', 
               help='generating only the code with the test cases')
    group.add_argument('-c','--only-compile', action="store_true" , dest='setOnlyCompile', 
               help='only compile the code generated by Map2Check-FORTES')

    args = parser.parse_args()        
    
    ############# Check options in the args
    ### vars to save data option
    
    pathCPrograms=''
    
    if args.dirCPrograms:                 
        if not os.path.isdir(args.dirCPrograms): 
            print('Error: unable to open find the dir (%s)' % args.dirCPrograms)
            parser.parse_args(['-h'])
            sys.exit()
        else:
            pathCPrograms = os.path.abspath(args.dirCPrograms)
            copy_api_library(pathCPrograms)
            if not args.setOnlyCode and not args.setOnlyCompile:
                set_codes_to_experiment(pathCPrograms)
    # improve this - TODO not work
    if args.setOnlyCode:
        only_generate_code(os.path.abspath(pathCPrograms))
    if args.setOnlyCompile:
        only_compile_code(os.path.abspath(pathCPrograms))
    