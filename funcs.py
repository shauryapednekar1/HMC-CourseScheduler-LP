"""Main Course Scheduling Script"""

import json
import time
import re
import os
import numpy as np

# Excel:
from excel.excel_parser import *

"""
OUTLINE:

         -- Get all courses offered next sem.
         -- Remove courses taken previously.
         -- Remove courses that cannot be taken due to prereqs.
         -- Remove next sem courses that I absolutely do not want to take/
            won"t get in to.
         -- Make a dictionary of of course name to variable name
            (and its index in "all_courses" string).
            
        --------
            
         --- Constraints ---
         
         -- Time conflict constraint matrix.
             Ax <= 1;     each row of A represents a discrete point in time
             
         -- No two same courses constraint matrix:
             Ax <= 1;     each row of A has a 1 for variables
                          that are the same course in different sections
                          
         -- Requirements constraint matrix.
            Ax >= r[i];   each row represents a requirement, and the entries 
                          of the row have 1 for the courses that fulfill that 
                          requirement

         -- Alternates constraint matrix.
            lower_bound[i] <= Ax <= upper_bound[i];   
            each row represents a set of alternates, and the entries 
            of the row have 1 are the courses in that set

        ------------
        
         -- Costs function

         -- Create .dat file

         -- Create exec.run file

     FINITO!
     
"""


##################################################
# Getting all courses that are going to be offered:

with open(r"rawData/course_data.json", encoding="utf-8") as f:
    raw_data = json.load(f)


def possible_courses_func():
    """
    Returns:
        list: all courses (with their complete course code) being offered
    """

    return list(raw_data["data"]["courses"].keys())


###############################################
# Only Keep 3 Credit Courses:


def only_keep_three_credit_classes(raw_data, possible_courses):
    """Removes all half credit/PE courses.

    Global Variables Needed:
        raw_data (dict, optional): Defaults to raw_data.
        possible_courses (list, optional): Defaults to possible_courses.

    Returns:
        list: possible three credit courses
    """
    possible = []

    for course in possible_courses:
        if raw_data["data"]["courses"][course]["courseCredits"] == "3.0":
            possible.append(course)

    return possible


#######################
# Remove Previously Taken Courses:


def remove_prev_courses(curr_previous_courses, possible_courses):
    """Removes previously taken courses.

    Global Variables Needed:
        curr_previous_courses (dict, optional): user"s previously taken courses.
        Defaults to curr_previous_courses.
        possible_courses (list, optional): Defaults to possible_courses.

    Returns:
        list: removes previously taken courses (all sections) from list of
        possible courses
    """
    # All sections of previously taken courses that are currently being offered
    repeated = set()

    for course in possible_courses:
        for prev_course in curr_previous_courses:
            # To find all sections of the prev_course
            if prev_course in course:
                repeated.add(course)

    # possible_courses minus repeated
    output = []
    for course in possible_courses:
        if course not in repeated:
            output.append(course)

    return output


######################
# Remove courses that cannot be taken due to prereqs:


def subject_codes_func(possible_courses):
    """Finds all possible subject codes (such as "MATH" and "RLST" etc.).

    Global Variables Needed:
        possible_courses (list, optional): Defaults to possible_courses.

    Returns:
        set: All unique subject codes
    """

    codes = set()
    for course in possible_courses:
        # Gets first word of course (until the first space)
        # - which is the subject code:
        curr_code = re.search(r"[^\s]+", course)
        if curr_code:
            curr_code = curr_code.group(0)
            if curr_code not in codes:
                codes.add(curr_code)

    return codes


with open(r"preReqs/prereqs_edited.json", encoding="utf-8") as f:
    prereqs_edited = json.load(f)


def helper_next_sem_possible_courses_due_to_prereqs(lis, curr_previous_courses):
    """Helper function that checks whether the prereqs for a course have been
    fulfilled

    Global Variables Needed:
        curr_previous_courses (set, optional): Defaults to curr_previous_courses.

    Args:
        lis (list): list of prereqs

    Returns:
        bool: True if prereqs have been fulfilled and false otherwise
    """
    for elem in lis:
        if elem not in curr_previous_courses:
            return False

    return True


def next_sem_possible_courses_due_to_prereqs(curr_previous_courses, possible_courses):
    """Creates list of possible courses according to previously taken courses
    and prereqs.

    Returns:
        list: list of possible courses according to previously taken courses
        and prereqs
    """

    list_of_possible_courses = []

    for course in possible_courses:

        # If the course has prereqs
        if course in prereqs_edited:
            curr_prereqs = prereqs_edited[course][1:]
            if ["POI"] in curr_prereqs:
                curr_prereqs.remove(["POI"])

            # If prereqs are fulfilled, True will be present in temp
            # Otherwise, it will be only False values

            temp = [
                helper_next_sem_possible_courses_due_to_prereqs(
                    prereq, curr_previous_courses
                )
                for prereq in curr_prereqs
            ]

            if True in temp:
                list_of_possible_courses.append(course)

        # If the course does not have prereqs
        else:
            list_of_possible_courses.append(course)

    return list_of_possible_courses


#####################
# Remove Courses Which Should Never Be Included in the Solution:


def remove_bad_courses(possible_courses, curr_bad_courses):
    """Removes courses which the user does not want included in the final output.

    Returns a list of all possible courses (minus the 'bad courses').
    """
    res = []

    removeCourses = set()
    for course in possible_courses:
        for bad_course in curr_bad_courses:
            if bad_course in course:
                removeCourses.add(course)

    for course in possible_courses:
        if course not in removeCourses:
            res.append(course)

    return res


######################
# Dictionary of course_name -> var_name and course_name -> var_index


def course_code_to_variable_and_index(possible_courses):
    """Dictionary that maps complate course code to a variable of the format
    "xi" where "i" is the variable number



    Global Variables Needed:
        possible_courses (list, optional): Defaults to possible_courses.

    Returns:
        tuple: tuple of two dictionaries:
                - course_to_variable_name: dict that maps complete course code
                to a variable of the format "xi" where "i" is the variable
                number

                - course_to_index: dict that maps complete_course_code to int i,
                  where i equals corresponding variable name in
                  course_to_variable_name

    """

    course_to_variable_name_dict = {}
    course_to_index_dict = {}
    j = 0

    for course in possible_courses:
        course_to_index_dict[course] = j
        course_to_variable_name_dict[course] = "x" + str(j)
        j += 1

    return course_to_variable_name_dict, course_to_index_dict


##########################
#################################### CONSTRAINTS ##################
##########################
# Time Conflict Constraint


def time_conflict_matrix_func(
    course_code_to_variable_name, course_to_index, raw_data, possible_courses
):
    """Creates a matrix that where each row represents the classes that are
    occuring during the time corresponding to that row.

    Global Variables Needed:
        course_to_variable_name (dict, optional):
        Defaults to course_to_variable_name.
        course_to_index (dict, optional): Defaults to course_to_index.
        raw_data (dict, optional): Defaults to raw_data.
        possible_courses (list, optional): Defaults to possible_courses.

    Returns:
        list of lists: 2-D Matrix where each element of each row is a
        zero or one where 1 correspondings to the class occuring during the time
        corresponding to its row and 0 otherwise.
    """

    # Produces a list of all the possible reasonable times in ten
    # minute intervals in the following format:
    # [0800, 0810, 0820, 0830, 0840, 0850, 0900, 0910, ...]
    discrete_times = []

    for k in range(7, 10):
        for j in range(0, 6):
            curr_time = "0" + str(k) + str(j) + "0"
            curr_time = int(curr_time)
            discrete_times.append(curr_time)

    for k in range(10, 24):
        for j in range(0, 6):
            curr_time = "0" + str(k) + str(j) + "0"
            curr_time = int(curr_time)
            discrete_times.append(curr_time)

    days = "MTWRF"

    constraint_matrix = []
    for curr_time in discrete_times:
        for day in days:
            curr_row = [0] * len(possible_courses)
            for curr_course in possible_courses:
                course = raw_data["data"]["courses"][curr_course]
                for item in course["courseSchedule"]:
                    if day in item["scheduleDays"]:
                        start_time = item["scheduleStartTime"]
                        end_time = item["scheduleEndTime"]

                        # Removing the colon from "hh:mm" and then converting it to an int
                        start_time = int(start_time[0:2] + start_time[3:])
                        end_time = int(end_time[0:2] + end_time[3:])

                        # Not strictly greater than or less than because
                        # courses can take place back to back.
                        after_start_time = curr_time > start_time
                        before_end_time = curr_time < end_time
                        if after_start_time and before_end_time:
                            curr_row[course_to_index[curr_course]] = 1

            constraint_matrix.append(curr_row)

    return constraint_matrix


################################
# No Two Same Courses Constraint:


def dict_w_same_codes_func(possible_courses):
    """Groups courses that are the same (but different
    sections/campuses) together

    Global Variables Needed:
        possible_courses (list, optional): Defaults to possible_courses.

    Returns:
        dict: Format of dictionary returned is
                {Course Code : [all courses that have the same course code]}
    """

    same_codes = {}
    for course in possible_courses:
        # Possible error for courses such as
        # "CSCI 181Y" isnt the same as "CSCI 181B"
        if course[0:8] in same_codes:
            same_codes[course[0:8]].append(course)
        else:
            same_codes[course[0:8]] = [course]

    return same_codes


def no_same_courses_matrix_func(possible_courses, course_to_index, dict_w_same_codes):
    """Creates constraint matrix that ensures that the solution provided
        doesn"t include two courses that are essentially
       the same but at different campuses or different timings.
       In the mod file, the following condition ensures it: Ax <= 1

    Global Variables Needed:
        dict_w_same_codes (dict, optional): Defaults to dict_w_same_codes.
        course_to_index (dict, optional): Defaults to course_to_index.
        possible_courses (list, optional): Defaults to possible_courses.

    Returns:
        List of lists: 2-D Matrix where the rows are the unique courses being
                       offered and the value of an element
                       in the row is a zero or one depending
                       on whether it is essentially the same course as its
                       corresponding row.
    """

    num_of_courses = len(possible_courses)

    constraint_matrix = []
    for key in dict_w_same_codes.keys():
        curr_row = [0] * num_of_courses
        for course in possible_courses:
            if key in course:
                curr_row[course_to_index[course]] = 1

        constraint_matrix.append(curr_row)

    return constraint_matrix


########## Requirements Constraint Matrix: ###############

hsa_codes = {
    "DANC",
    "WRIT",
    "ORST",
    "PPA",
    "DS",
    "ARBT",
    "JAPN",
    "CHNT",
    "MSL",
    "CASA",
    "ASIA",
    "ART",
    "GWS",
    "GREK",
    "GLAS",
    "LATN",
    "SPEC",
    "GOVT",
    "RUST",
    "HMSC",
    "SPCH",
    "CHST",
    "CREA",
    "PORT",
    "LEAD",
    "ARCN",
    "SPAN",
    "ITAL",
    "MLLC",
    "MES",
    "MS",
    "PPE",
    "RLIT",
    "LGST",
    "POST",
    "LAST",
    "FREN",
    "RUSS",
    "STS",
    "GEOG",
    "GRMT",
    "ARBC",
    "FHS",
    "AMST",
    "POLI",
    "ARHI",
    "MUS",
    "MENA",
    "LGCS",
    "CLAS",
    "KRNT",
    "LIT",
    "JPNT",
    "ENGL",
    "MCBI",
    "CGS",
    "FS",
    "HIST",
    "CHLT",
    "CHIN",
    "SOC",
    "MOBI",
    "FLAN",
    "ECON",
    "MCSI",
    "EA",
    "ANTH",
    "FIN",
    "EDUC",
    "PHIL",
    "GEOL",
    "RLST",
    "FWS",
    "THEA",
    "IR",
    "GERM",
    "ID",
    "ASAM",
    "HSA",
    "KORE",
    "HUM",
    "AFRI",
    "PSYC",
}

# Majors:

# CS-MATH Major
def cs_math_major_reqs_matrix_func(
    possible_courses, curr_previous_courses, dict_w_same_codes, course_to_index
):
    """Creates a constraint matrix for the CS-MATH major.

    Args:
        possible_courses ([type]): [description]
        curr_previous_courses ([type]): [description]
        dict_w_same_codes ([type]): [description]
        course_to_index ([type]): [description]

    Returns:
        [type]: [description]
    """
    num_rows = 6  # 6 requirements for the CS-math major

    constraint_matrix = np.zeros(shape=(num_rows, len(possible_courses)), dtype=int)

    for course in possible_courses:
        curr_code = re.search(r"[^\s]+", course)
        if curr_code:
            curr_code = curr_code.group(0)

        # First Row: Four Kernel Courses in Computer Science and Mathematics
        if (
            (course[0:8] == "MATH 055")
            or (course[0:8] == "CSCI 060")
            or (course[0:8] == "CSCI 081")
            or (course[0:8] == "CSCI 140")
        ):

            contraint_matrix[0][course_to_index[course]] = 1

        # Second Row: Two Computer Science Courses
        elif (course[0:8] == "CSCI 070") or (course[0:8] == "CSCI 131"):
            constraint_matrix[1][course_to_index[course]] = 1

        # Third Row: Two Mathematics Courses
        elif (course[0:8] == "MATH 131") or (course[0:8] == "MATH 171"):
            constraint_matrix[2][course_to_index[course]] = 1

        # Fourth Row: Clinic
        elif (course[0:8] == "CSMT 183") or (course[0:8] == "CSMT 184"):
            constraint_matrix[3][course_to_index[course]] = 1

        # Fifth Row: Math courses above 100
        # (TODO: need to remove "strange" courses)
        elif course[0:6] == "MATH 1":
            constraint_matrix[4][course_to_index[course]] = 1

        # Sixth Row: CS courses above 100
        # (TODO: need to remove "strange" courses):
        elif course[0:6] == "CSCI 1":
            constraint_matrix[5][course_to_index[course]] = 1

    return list(constraint_matrix)


# CS Major
def cs_major_reqs_matrix_func(
    possible_courses, curr_previous_courses, dict_w_same_codes, course_to_index
):

    num_rows = 4  # 4 requirements for the CS major

    constraint_matrix = np.zeros(shape=(num_rows, len(possible_courses)), dtype=int)

    for course in possible_courses:
        curr_code = re.search(r"[^\s]+", course)
        if curr_code:
            curr_code = curr_code.group(0)

        cs_foundation_requirement_courses = {
            "CSCI 060",
            "CSCI 042",
            "MATH 055",
            "CSCI 070",
            "CSCI 081",
        }

        cs_kernel_requirement_courses = {"CSCI 105", "CSCI 121", "CSCI 131", "CSCI 140"}

        cs_not_elective_requirement_courses = {
            "CSCI 195",
            "CSCI 192",
            "CSCI 191",
            "CSCI 190",
            "CSCI 189",
            "CSCI 188",
            "CSCI 184",
            "CSCI 183",
        }

        # First Row: CS Foundation Requirement
        if course[0:8] in cs_foundation_requirement_courses:
            contraint_matrix[0][course_to_index[course]] = 1

        # Second Row: CS Kernel Requirement
        elif course[0:8] in cs_kernel_requirement_courses:
            constraint_matrix[1][course_to_index[course]] = 1

        # Third Row: CS Elective Requirement
        # CS courses above 100
        elif (course[0:6] == "CSCI 1") and (
            course[0:8] not in cs_not_elective_requirement_courses
        ):
            constraint_matrix[2][course_to_index[course]] = 1

        # Fourth Row: Clinic
        elif (course[0:8] == "CSMT 183") or (course[0:8] == "CSMT 184"):
            constraint_matrix[3][course_to_index[course]] = 1

    return list(constraint_matrix)


# ENGR Major
def engr_major_reqs_matrix_func(
    possible_courses, curr_previous_courses, dict_w_same_codes, course_to_index
):

    num_rows = 5  # 5 requirements for the Engr major

    constraint_matrix = np.zeros(shape=(num_rows, len(possible_courses)), dtype=int)

    for course in possible_courses:
        curr_code = re.search(r"[^\s]+", course)
        if curr_code:
            curr_code = curr_code.group(0)

        engr_design_requirement_courses = {"ENGR 004", "ENGR 080"}

        engr_systems_requirement_courses = {"ENGR 079", "ENGR 101", "ENGR 102"}

        engr_science_requirement_courses = {
            "ENGR 082",
            "ENGR 083",
            "ENGR 084",
            "ENGR 085",
            "ENGR 086",
        }

        engr_clinic_courses = {"ENGR 111", "ENGR 112", "ENGR 113"}

        # First Row: Engineering Design Requirement (w/o clinic)
        if course[0:8] in engr_design_requirement_courses:
            contraint_matrix[0][course_to_index[course]] = 1

        # Second Row: Engineering Systems Requirement
        elif course[0:8] in engr_systems_requirement_courses:
            constraint_matrix[1][course_to_index[course]] = 1

        # Third Row: Engr Science Requirement (e72 not added since its a half sem course)
        elif course[0:8] in engr_science_requirement_courses:
            constraint_matrix[2][course_to_index[course]] = 1

        # Fourth Row: Clinic
        elif course[0:8] in engr_clinic_courses:
            constraint_matrix[3][course_to_index[course]] = 1

        # Fifth Row: Electives
        elif course[0:4] == "ENGR":
            constraint_matrix[4][course_to_index[course]] = 1

    return list(constraint_matrix)


# HSA:
def hsa_reqs_matrix(
    possible_courses,
    curr_previous_courses,
    dict_w_same_codes,
    course_to_index,
    hsa_codes,
    hsa_concentration,
):

    # Needed for HSA breadth requirement
    prev_course_codes = set()
    for course in curr_previous_courses:
        curr_code = re.search(r"[^\s]+", course)
        if curr_code:
            curr_code = curr_code.group(0)
            if curr_code not in prev_course_codes:
                prev_course_codes.add(curr_code)

    num_of_courses = len(possible_courses)
    hsa_constraint_matrix = np.zeros(shape=(4, num_of_courses), dtype=int)

    for course in possible_courses:
        curr_code = re.search(r"[^\s]+", course)
        if curr_code:
            curr_code = curr_code.group(0)

        # HSA Requirements (this stays the same for all majors):
        if curr_code in hsa_codes:

            # Seventh Row: HSA Breadth Requirement
            if curr_code != hsa_concentration:
                if curr_code not in prev_course_codes:
                    hsa_constraint_matrix[0][course_to_index[course]] = 1

            # Eight Row: HSA Concentration Requirement
            else:
                hsa_constraint_matrix[1][course_to_index[course]] = 1

            # Ninth Row: HSA Mudd Hum Requirement
            t = course.split(" ")
            if t[2][0:2] == "HM":
                hsa_constraint_matrix[2][course_to_index[course]] = 1

            # Tenth Row: HSA General Requirement
            hsa_constraint_matrix[3][course_to_index[course]] = 1

    return list(hsa_constraint_matrix)


# All Reqs:


def requirements_matrix_func(
    possible_courses,
    curr_previous_courses,
    dict_w_same_codes,
    course_to_index,
    hsa_codes,
    hsa_concentration,
):
    """Creates matrix that ensures that desired requirements are met.

    1. Requirements (currently only designed for CS-Math, CS, and ENGR majors):
    (This will be based on what the student chooses for the next semester.)

    Not adding Colloquia Row :--> because its not really a constraint
    since it doesnt have a fixed time nor does it count towards an overload

    Global Variables Needed:
        dict_w_same_codes ([type], optional): Defaults to dict_w_same_codes.
        course_to_index ([type], optional): Defaults to course_to_index.
        possible_courses ([type], optional): Defaults to possible_courses.
        hsa_codes ([type], optional): Defaults to hsa_codes.
        hsaConcentration ([type], optional): Defaults to hsaConcentration.
        curr_previous_courses ([type], optional): Defaults to curr_previous_courses.

    Returns:
        List of lists: 2-D Matrix where each row represents a
        specific requirement and each column represents a specific course
    """
    major_matrix = []
    if curr_major == "CS-MATH":
        major_matrix = cs_math_major_reqs_matrix_func(
            possible_courses, curr_previous_courses, dict_w_same_codes, course_to_index
        )
    elif curr_major == "CS":
        major_matrix = cs_major_reqs_matrix_func(
            possible_courses, curr_previous_courses, dict_w_same_codes, course_to_index
        )
    elif curr_major == "ENGR":
        major_matrix = engr_major_reqs_matrix_func(
            possible_courses, curr_previous_courses, dict_w_same_codes, course_to_index
        )

    hsa_matrix = hsa_reqs_matrix(
        possible_courses,
        curr_previous_courses,
        dict_w_same_codes,
        course_to_index,
        hsa_codes,
        hsa_concentration,
    )

    return major_matrix + hsa_matrix


########## Alternates Constraint Matrix: ###############


def alternates_matrix_func(curr_alternates, possible_courses, course_to_index):
    n = len(possible_courses)
    matrix = []
    for item in curr_alternates:
        curr_row = [0] * n
        alt_courses = item[0]
        alt_limit = item[1]  # Unused
        for course in possible_courses:
            for alt in alt_courses:
                if alt in course:
                    curr_row[course_to_index[course]] = 1

        matrix.append(curr_row)

    return matrix


######################################
######################### COSTS: ###############


def costs_func(
    possible_courses, course_to_index, curr_preferences, curr_default_preferences
):
    """Row of costs corresponding to each possible course.

    Global Variables Needed:
        possible_courses (list, optional): Defaults to possible_courses.
        course_to_index (dict, optional): Defaults to course_to_index.
        curr_preferences (dict, optional): Defaults to myPreferences.
        default_preferences:

    Returns:
        List: Row of costs corresponding to each possible course.
    """
    num_of_courses = len(possible_courses)
    costs_row = [0] * num_of_courses
    for course in possible_courses:
        if course in curr_preferences:
            costs_row[course_to_index[course]] = curr_preferences[course]
        # Default costs for courses
        else:
            check = False  # Changes to true if course gets a default preference, otherwise the course gets the base ranking
            for default_course_preference in curr_default_preferences:
                # format is: default_course_preference = [course, ranking]
                if default_course_preference[0] in course:
                    costs_row[course_to_index[course]] = default_course_preference[1]
                    check = True
                    break

            if not check:  # course is not in preferences or default preferences
                costs_row[course_to_index[course]] = curr_base_ranking
        # else:
        #     # CS Courses = Cost of 5
        #     if course[0:4] == "CSCI":
        #         costs_row[course_to_index[course]] = 0
        #     # ENGR Courses = Cost of 4
        #     elif course[0:4] == "ENGR":
        #         costs_row[course_to_index[course]] = 7
        #     # Math Courses = Cost of 4
        #     elif course[0:4] == "MATH":
        #         costs_row[course_to_index[course]] = 0
        #     # Philosophy Courses = Cost of 3
        #     elif course[0:4] == "PHIL":
        #         costs_row[course_to_index[course]] = 0
        #     # All other courses = Cost of 2
        #     else:
        #         costs_row[course_to_index[course]] = 3

    return costs_row


######################################
# Creating .dat file:


def createDat(dir_path, filename, curr_num_reqs):
    res = ""

    with open(dir_path + r"costs_names.txt", "r") as f:
        costs_names = f.read()

    with open(dir_path + r"course_names.txt", "r") as f:
        course_names = f.read()

    with open(dir_path + r"requirements_matrix.txt", "r") as f:
        requirements_matrix = f.read()

    with open(dir_path + r"set_timeSlots.txt", "r") as f:
        set_timeSlots = f.read()

    with open(dir_path + r"set_uniqueCourses.txt", "r") as f:
        set_uniqueCourses = f.read()

    with open(dir_path + r"time_conflict_matrix.txt", "r") as f:
        time_conflict_matrix = f.read()

    with open(dir_path + r"unique_courses_matrix.txt", "r") as f:
        unique_courses_matrix = f.read()

    with open(dir_path + r"set_alternates.txt", "r") as f:
        set_alternates = f.read()

    with open(dir_path + r"alternates_matrix.txt", "r") as f:
        alternates_matrix = f.read()

    with open(dir_path + r"alternates_lower_limits.txt", "r") as f:
        alternates_lower_limits = f.read()

    with open(dir_path + r"alternates_upper_limits.txt", "r") as f:
        alternates_upper_limits = f.read()

    res += "set courses := "
    res += "\n    "
    res += course_names + "\n;"
    res += "\n\n"

    res += "set requirements := "
    res += "\n    "
    res += curr_num_reqs + "\n;"
    res += "\n\n"

    res += "set timeSlots := "
    res += "\n    "
    res += set_timeSlots + "\n;"
    res += "\n\n"

    res += "set uniqueCourses := "
    res += "\n    "
    res += set_uniqueCourses + "\n;"
    res += "\n\n"

    res += "set alternates := "
    res += "\n    "
    res += set_alternates + "\n;"
    res += "\n\n"

    res += "param costs := "
    res += "\n    "
    res += costs_names + "\n;"
    res += "\n\n"

    res += "param time : "
    res += "\n    "
    res += course_names + " := \n"
    res += "\n    "
    res += time_conflict_matrix + "\n;"
    res += "\n\n"

    res += "param counts : "
    res += "\n    "
    res += course_names + " := \n"
    res += "\n    "
    res += requirements_matrix + "\n;"
    res += "\n\n"

    res += "param necessary := "
    res += "\n    "
    res += curr_desired_reqs + "\n;"
    res += "\n\n"

    res += "param unique : "
    res += "\n    "
    res += course_names + " := \n"
    res += "\n    "
    res += unique_courses_matrix + "\n;"
    res += "\n\n"

    res += "param alternatesLowerLimits := "
    res += "\n    "
    res += alternates_lower_limits + "\n;"
    res += "\n\n"

    res += "param alternatesUpperLimits := "
    res += "\n    "
    res += alternates_upper_limits + "\n;"
    res += "\n\n"

    res += "param alternatesMatrix : "
    res += "\n    "
    res += course_names + " := \n"
    res += "\n    "
    res += alternates_matrix + "\n;"
    res += "\n\n"

    with open(r"./amplFiles/" + filename, "w") as fp:
        fp.write(res)


#####################################
# Creating exec.run file:


def create_ampl_command(dat_filename):

    data_file = "\\" + dat_filename + ".dat"

    ampl_mod_command = f"{os.getcwd()}\\amplFiles\\model.mod;"

    ampl_dat_command = f"{os.getcwd()}\\amplFiles{data_file};"

    ampl_solve_command = r"solve;"

    ampl_option_command = r"option omit_zero_rows 1;"

    ampl_solver_command = r"option solver './cplex';"

    ampl_display_command = r"display x;"

    ampl_all_commands = (
        ampl_mod_command
        + "\n"
        + ampl_dat_command
        + "\n"
        + ampl_solver_command
        + "\n"
        + ampl_solve_command
        + "\n"
        + ampl_option_command
        + "\n"
        + ampl_display_command
    )

    with open("exec.run", "w") as f:
        f.write(ampl_all_commands)


#####################################
