from . import citationchecker
from . import linkchecker
from . import sizechecker
from . import tests_config
from modules import site_config
from modules import util
import os 
import shutil

def run_tests():
    """Run tests"""

    error_list = []
    tests = 0

    print("\nRunning tests:")
    util.buildhelpers.print_test_output("-", "-", "-")
    util.buildhelpers.print_test_output("STATUS","TEST","MESSAGE")
    util.buildhelpers.print_test_output("-", "-", "-") 

    # Check output size
    if (site_config.args.tests and 'size' in site_config.args.tests) or not site_config.args.tests:
        tests += 1
        if check_size() == tests_config.SIZE_ERROR:
            error_list.append(tests_config.SIZE_ERROR)

    # Check internal links
    if (site_config.args.tests and ('links' in site_config.args.tests or 'external_links' in site_config.args.tests)) or not site_config.args.tests:
        tests += 3
        # Check external and internal links if external link flag was set. 
        # Only check internal links if not set
        if site_config.args.tests:
            do_external = "external_links" in site_config.args.tests
        else:
            do_external = False
        exit_codes, broken_links_count, unlinked_pages, relative_links = check_links(do_external)

        error_list.extend(
            exit_code
            for exit_code in exit_codes
            if exit_code != tests_config.SUCCESS
        )

    # Check citations
    if (site_config.args.tests and 'citations' in site_config.args.tests) or not site_config.args.tests:
        tests += 1
        exit_code, broken_citations_count = check_citations()
        if exit_code == tests_config.BROKEN_CITATION:
            error_list.append(tests_config.BROKEN_CITATION)

    util.buildhelpers.print_test_output("-", "-", "-")

    # Successful tests vs failed tests
    if (tests - len(error_list)) == 1:
        if len(error_list) == 1:
            print(
                f"\n{tests - len(error_list)} test passed, {len(error_list)} test failed\n"
            )

        else:
            print(
                f"\n{tests - len(error_list)} test passed, {len(error_list)} tests failed\n"
            )

    elif len(error_list) == 1:
        print(
            f"\n{tests - len(error_list)} tests passed, {len(error_list)} test failed\n"
        )

    else:
        print(
            f"\n{tests - len(error_list)} tests passed, {len(error_list)} tests failed\n"
        )


    if error_list:
        if tests_config.BROKEN_CITATION in error_list:
            # Print report if less than six broken citations
            if broken_citations_count < 6 or site_config.args.print_tests:
                with open(
                        os.path.join(tests_config.test_report_directory, tests_config.citations_report_filename), "r", 
                        encoding='utf-8') as citations_report:
                    print(citations_report.read())
            else:
                print(
                    f"Broken citations report written to {os.path.join(tests_config.test_report_directory, tests_config.citations_report_filename)}"
                )


        if tests_config.BROKEN_LINKS in error_list or tests_config.BROKEN_EXTERNAL_LINKS in error_list:
            if broken_links_count < 6 or site_config.args.print_tests:
                # Print report if less than six broken citations
                with open(
                        os.path.join(tests_config.test_report_directory, tests_config.links_report_filename), "r", 
                        encoding='utf-8') as links_report:
                    print(links_report.read())
            else:
                print(
                    f"Broken links report written to {os.path.join(tests_config.test_report_directory, tests_config.links_report_filename)}"
                )


        if tests_config.UNLINKED_PAGES in error_list:
            # Print report if flag is stated
            if unlinked_pages < 6 or site_config.args.print_tests:
                with open(
                        os.path.join(tests_config.test_report_directory, tests_config.unlinked_report_filename), "r", 
                        encoding='utf-8') as unlinked_report:
                    print(unlinked_report.read())
            else:
                print(
                    f"Unlinked pages report written to {os.path.join(tests_config.test_report_directory, tests_config.unlinked_report_filename)}"
                )

        if tests_config.RELATIVE_LINKS_FOUND in error_list:
            # Print report if flag is stated
            if relative_links < 6 or site_config.args.print_tests:
                with open(
                        os.path.join(tests_config.test_report_directory, tests_config.relative_links_report_filename), "r", 
                        encoding='utf-8') as relative_links_report:
                    print(relative_links_report.read())
            else:
                print(
                    f"Unlinked pages report written to {os.path.join(tests_config.test_report_directory, tests_config.relative_links_report_filename)}"
                )


    if not site_config.args.override_exit_status:
        handle_exit(error_list)

def check_links(external_links):
    """Wrapper to check internal and/or external links"""

    # Link test

    TEST = "Links"

    util.buildhelpers.print_test_output("RUNNING",TEST,"-")

    exit_codes, links, unlinked_pages, relative_links = linkchecker.check_links(external_links)

    if tests_config.BROKEN_LINKS in exit_codes:
        STATUS = tests_config.FAILED_STATUS
    elif tests_config.BROKEN_EXTERNAL_LINKS in exit_codes:
        STATUS = tests_config.WARNING_STATUS
    else:
        STATUS = tests_config.PASSED_STATUS

    TEST = "Internal/External Links" if external_links else "Internal Links"
    MSG = f"{links[0]} OK - {links[1]} broken link(s) "

    # Print output
    util.buildhelpers.print_test_output(STATUS,TEST,MSG)

    # Unlinked pages test
    TEST = "Unlinked Pages"

    if tests_config.UNLINKED_PAGES in exit_codes:
        STATUS = tests_config.WARNING_STATUS
    else:
        STATUS = tests_config.PASSED_STATUS

    MSG = f"{unlinked_pages} unlinked page(s)"

    util.buildhelpers.print_test_output(STATUS,TEST,MSG)

    # Unlinked pages test
    TEST = "Relative Links"

    if tests_config.RELATIVE_LINKS_FOUND in exit_codes:
        STATUS = tests_config.WARNING_STATUS
    else:
        STATUS = tests_config.PASSED_STATUS

    MSG = f"{relative_links} page(s) with relative link(s) found"

    util.buildhelpers.print_test_output(STATUS,TEST,MSG)

    return exit_codes, links[1], unlinked_pages, relative_links

def check_citations():
    """Wrapper to check for broken citations"""

    TEST = "Broken Citations"

    util.buildhelpers.print_test_output("RUNNING",TEST,"-")

    exit_code, pages = citationchecker.citations_check()

    if exit_code == tests_config.SUCCESS:
        STATUS = tests_config.PASSED_STATUS
    else:
        STATUS = tests_config.FAILED_STATUS

    if pages[1] == 1:
        MSG = f"{pages[0]} pages OK, {pages[1]} page broken"
    else:
        MSG = f"{pages[0]} pages OK, {pages[1]} pages broken"

    util.buildhelpers.print_test_output(STATUS,TEST,MSG)

    return exit_code, pages[1]

def check_size():
    """Wrapper to check output size for Github's limit"""

    TEST = "Output Folder Size"

    util.buildhelpers.print_test_output("RUNNING",TEST,"-")

    exit_code, size_MB = sizechecker.check_output_size()

    if exit_code == tests_config.SUCCESS:
        STATUS = tests_config.PASSED_STATUS
        MSG = f"Size: {size_MB:.2f} MB"

    elif exit_code == tests_config.WARNING:
        STATUS = tests_config.WARNING_STATUS
        MSG = f"Approaching 1 GB limit: {size_MB:.2f} MB"
    else:
        STATUS = tests_config.FAILED_STATUS
        MB_TO_GB_CONVERSION = 1000

        MSG = "Surpassed 1 GB limit: " \
                f"{size_MB/MB_TO_GB_CONVERSION:.3f} GB" + tests_config.RESET

    util.buildhelpers.print_test_output(STATUS,TEST,MSG)

    return exit_code

def handle_exit(exit_codes):
    """Given a exit codes list, exit with 1 on failure and 0 on success
       for CI
    """

    # Check if exit codes list is not empty
    if exit_codes and (
        tests_config.BROKEN_CITATION in exit_codes
        or tests_config.BROKEN_LINKS in exit_codes
        or tests_config.SIZE_ERROR in exit_codes
    ):
        exit(tests_config.FAILURE)