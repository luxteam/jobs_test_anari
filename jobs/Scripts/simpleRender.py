import argparse
import os
import subprocess
import psutil
import json
import platform
from datetime import datetime
from shutil import copyfile, move
import sys
from utils import is_case_skipped
from queue import Queue
from subprocess import PIPE, Popen
from threading import Thread
import traceback
import time
import copy

sys.path.append(os.path.abspath(os.path.join(
    os.path.dirname(__file__), os.path.pardir, os.path.pardir)))
from jobs_launcher.core.config import *
from jobs_launcher.core.system_info import get_gpu


def copy_test_cases(args):
    try:
        copyfile(os.path.realpath(os.path.join(os.path.dirname(
            __file__), '..', 'Tests', args.test_group, 'test_cases.json')),
            os.path.realpath(os.path.join(os.path.abspath(
                args.output), 'test_cases.json')))

        cases = json.load(open(os.path.realpath(
            os.path.join(os.path.abspath(args.output), 'test_cases.json'))))

        with open(os.path.join(os.path.abspath(args.output), "test_cases.json"), "r") as json_file:
            cases = json.load(json_file)

        if os.path.exists(args.test_cases) and args.test_cases:
            with open(args.test_cases) as file:
                test_cases = json.load(file)['groups'][args.test_group]
                if test_cases:
                    necessary_cases = [
                        item for item in cases if item['case'] in test_cases]
                    cases = necessary_cases

            with open(os.path.join(args.output, 'test_cases.json'), "w+") as file:
                json.dump(duplicated_cases, file, indent=4)
    except Exception as e:
        main_logger.error('Can\'t load test_cases.json')
        main_logger.error(str(e))
        exit(-1)


def copy_baselines(args, case, baseline_path, baseline_path_tr):
    try:
        copyfile(os.path.join(baseline_path_tr, case['case'] + CASE_REPORT_SUFFIX),
                 os.path.join(baseline_path, case['case'] + CASE_REPORT_SUFFIX))

        with open(os.path.join(baseline_path, case['case'] + CASE_REPORT_SUFFIX)) as baseline:
            baseline_json = json.load(baseline)

        for thumb in [''] + THUMBNAIL_PREFIXES:
            if os.path.exists(os.path.join(baseline_path_tr, baseline_json[thumb + 'render_color_path'])):
                copyfile(os.path.join(baseline_path_tr, baseline_json[thumb + 'render_color_path']),
                         os.path.join(baseline_path, baseline_json[thumb + 'render_color_path']))
    except:
        main_logger.error('Failed to copy baseline ' +
                                      os.path.join(baseline_path_tr, case['case'] + CASE_REPORT_SUFFIX))


def prepare_empty_reports(args, current_conf):
    main_logger.info('Create empty report files')

    baseline_path = os.path.join(args.output, os.path.pardir, os.path.pardir, os.path.pardir, 'Baseline', args.test_group)

    if not os.path.exists(baseline_path):
        os.makedirs(baseline_path)
        os.makedirs(os.path.join(baseline_path, 'Color'))

    baseline_dir = 'rpr_anari_autotests_baselines'

    if platform.system() == 'Windows':
        baseline_path_tr = os.path.join('c:/TestResources', baseline_dir, args.test_group)
    else:
        baseline_path_tr = os.path.expandvars(os.path.join('$CIS_TOOLS/../TestResources', baseline_dir, args.test_group))

    copyfile(os.path.abspath(os.path.join(args.output, '..', '..', '..', '..', 'jobs_launcher',
                                          'common', 'img', 'error.png')), os.path.join(args.output, 'Color', 'failed.jpg'))

    with open(os.path.join(os.path.abspath(args.output), "test_cases.json"), "r") as json_file:
        cases = json.load(json_file)

    for case in cases:
        if is_case_skipped(case, current_conf):
            case['status'] = 'skipped'

        if case['status'] != 'done' and case['status'] != 'error':
            if case["status"] == 'inprogress':
                case['status'] = 'active'
            elif case["status"] == 'inprogress_observed':
                case['status'] = 'observed'

            test_case_report = RENDER_REPORT_BASE.copy()
            test_case_report['test_case'] = case['case']
            test_case_report['render_device'] = get_gpu()
            test_case_report['render_duration'] = -0.0
            test_case_report['script_info'] = case['script_info']
            test_case_report['library'] = args.library
            test_case_report['test_group'] = args.test_group
            test_case_report['tool'] = 'Anari'
            test_case_report['date_time'] = datetime.now().strftime(
                '%m/%d/%Y %H:%M:%S')

            if case['status'] == 'skipped':
                test_case_report['test_status'] = 'skipped'
                test_case_report['file_name'] = case['case'] + case.get('extension', '.jpg')
                test_case_report['render_color_path'] = os.path.join('Color', test_case_report['file_name'])
                test_case_report['group_timeout_exceeded'] = False

                try:
                    skipped_case_image_path = os.path.join(args.output, 'Color', test_case_report['file_name'])
                    if not os.path.exists(skipped_case_image_path):
                        copyfile(os.path.join(args.output, '..', '..', '..', '..', 'jobs_launcher', 
                            'common', 'img', "skipped.jpg"), skipped_case_image_path)
                except OSError or FileNotFoundError as err:
                    main_logger.error("Can't create img stub: {}".format(str(err)))
            else:
                test_case_report['test_status'] = 'error'
                test_case_report['file_name'] = 'failed.jpg'
                test_case_report['render_color_path'] = os.path.join('Color', 'failed.jpg')

            case_path = os.path.join(args.output, case['case'] + CASE_REPORT_SUFFIX)

            with open(case_path, "w") as f:
                f.write(json.dumps([test_case_report], indent=4))

        copy_baselines(args, case, baseline_path, baseline_path_tr)
    with open(os.path.join(args.output, "test_cases.json"), "w+") as f:
        json.dump(cases, f, indent=4)


def read_output(pipe, functions):
    for line in iter(pipe.readline, b''):
        for function in functions:
            function(line.decode('utf-8'))
    pipe.close()


def save_results(args, cases, render_time, timeout_exceeded, error_messages = []):
    render_time_set = False

    for case in cases:
        if case["status"] == "skipped":
            continue

        with open(os.path.join(args.output, case["case"] + CASE_REPORT_SUFFIX), "r") as file:
            test_case_report = json.loads(file.read())[0]

            if not render_time_set:
                test_case_report["render_time"] = render_time
                render_time_set = True

            test_case_report["testing_start"] = datetime.now().strftime("%m/%d/%Y %H:%M:%S")

            images_output_path = os.path.split(args.tool)[0]
            output_image_path = os.path.join(images_output_path, case["case"] + case.get("extension", '.png'))
            target_image_path = os.path.join(args.output, "Color", case["case"] + case.get("extension", '.png'))

            if os.path.exists(output_image_path):
                copyfile(output_image_path, target_image_path)

                test_case_report["file_name"] = case["case"] + case.get("extension", '.png')
                test_case_report["render_color_path"] = os.path.join("Color", test_case_report["file_name"])

                if case['status'] == "active":
                    test_case_report["test_status"] = "passed"
                elif case['status'] == "observed":
                    test_case_report["test_status"] = "observed"

                case["status"] = "done"
            else:
                messages = copy.deepcopy(error_messages)
                message = "Output image not found"
                messages.append(message)
                test_case_report["message"] = list(messages)
                case["status"] = test_case_report["test_status"]

            if not timeout_exceeded:
                test_case_report["group_timeout_exceeded"] = False

        with open(os.path.join(args.output, case["case"] + CASE_REPORT_SUFFIX), "w") as file:
            json.dump([test_case_report], file, indent=4)

    with open(os.path.join(args.output, "test_cases.json"), "w") as file:
        json.dump(cases, file, indent=4)


def execute_tests(args, current_conf):
    rc = 0

    with open(os.path.join(os.path.abspath(args.output), "test_cases.json"), "r") as json_file:
        cases = json.load(json_file)

    if platform.system() == "Windows":
        import win32gui
        import win32con
        execution_script = "{tool} --library {library}".format(tool=os.path.abspath(args.tool), library=args.library)
        execution_script_path = os.path.join(args.output, 'script.bat')
        with open(execution_script_path, "w") as f:
            f.write(execution_script)
    else:
        if platform.system() == "Linux":
            execution_script = "#!/bin/sh\nexport LD_LIBRARY_PATH={anari_path}:/usr/local/lib; {tool} --library {library}".format(
                anari_path=os.path.split(args.tool)[0], tool=os.path.abspath(args.tool), library=args.library)
        else:
            execution_script = "#!/bin/sh\nexport LD_LIBRARY_PATH={anari_path}; {tool} --library {library}".format(
                anari_path=os.path.split(args.tool)[0], tool=os.path.abspath(args.tool), library=args.library)

        execution_script_path = os.path.join(args.output, 'script.sh')
        with open(execution_script_path, "w") as f:
            f.write(execution_script)
        os.system('chmod +x {}'.format(execution_script_path))

    os.chdir(os.path.split(args.tool)[0])

    p = psutil.Popen(execution_script_path, shell=False,
                     stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    outs = []
    queue = Queue()

    stdout_thread = Thread(target=read_output, args=(p.stdout, [queue.put, outs.append]))

    start_time = time.time()

    stdout_thread.daemon = True
    stdout_thread.start()

    timeout = args.timeout
    check_time = 10

    error_messages = []

    case_finished = False

    try:
        while not case_finished:
            try:
                p.wait(timeout=check_time)
            except (psutil.TimeoutExpired, subprocess.TimeoutExpired) as e:
                for out in outs:
                    if "[ERROR]" in out:
                        message = "Some error appeared"
                        error_messages.append(message)
                        raise Exception(message)

                timeout -= check_time

                if timeout <= 0:
                    message = "Abort tests execution due to timeout"
                    error_messages.append(message)
                    raise Exception(message)

                if platform.system() == "Windows":
                    crash_window = win32gui.FindWindow(None, "Microsoft Visual C++ Runtime Library")

                    if crash_window:
                        message = "Crash window was found"
                        error_messages.append(message)
                        win32gui.PostMessage(crash_window, win32con.WM_CLOSE, 0, 0)
                        raise Exception(message)
            else:
                main_logger.info("Render finished")

                for out in outs:
                    if "[ERROR]" in out:
                        message = "Some error appeared"
                        error_messages.append(message)
                        raise Exception(message)

                case_finished = True

    except Exception as e:
        main_logger.error(e)

        try:
            for child in reversed(p.children(recursive=True)):
                child.terminate()
            p.terminate()
        except Exception as e1:
            main_logger.error("Failed to terminate running process: {}".format(e1))

        rc = -1
    finally:
        render_time = time.time() - start_time
        save_results(args, cases, render_time, timeout <= 0, error_messages=error_messages)

        log_path = os.path.join(args.output, "renderTool.log")

        with open(log_path, "a", encoding="utf-8") as file:
            while not queue.empty():
                file.write(queue.get())

    return rc


def createArgsParser():
    parser = argparse.ArgumentParser()

    parser.add_argument("--tool", required=True, metavar="<path>")
    parser.add_argument("--output", required=True, metavar="<dir>")
    parser.add_argument("--test_group", required=True)
    parser.add_argument("--test_cases", required=True)
    parser.add_argument('--timeout', required=False, default=600)
    parser.add_argument('--library', required=True)
    parser.add_argument('--update_refs', required=True)

    return parser


if __name__ == '__main__':
    main_logger.info('simpleRender start working...')

    args = createArgsParser().parse_args()

    try:
        if not os.path.exists(os.path.join(args.output, "Color")):
            os.makedirs(os.path.join(args.output, "Color"))

        render_device = get_gpu()
        system_pl = platform.system()
        current_conf = set(platform.system()) if not render_device else {platform.system(), render_device}
        main_logger.info("Detected GPUs: {}".format(render_device))
        main_logger.info("PC conf: {}".format(current_conf))
        main_logger.info("Creating predefined errors json...")

        copy_test_cases(args)
        prepare_empty_reports(args, current_conf)
        exit(execute_tests(args, current_conf))
    except Exception as e:
        main_logger.error("Failed during script execution. Exception: {}".format(str(e)))
        main_logger.error("Traceback: {}".format(traceback.format_exc()))
        exit(-1)
