from project import app, engine
from sqlalchemy import *
from flask import request, render_template, g, redirect, url_for,flash
from flask_login import login_user, logout_user, current_user, login_required
from project.user import User

is_student = False

@app.before_request
def before_request():
  try:
    g.conn = engine.connect()
  except:
    print ("uh oh, problem connecting to database")
    import traceback; traceback.print_exc()
    g.conn = None

@app.teardown_request
def teardown_request(exception):
  try:
    g.conn.close()
  except Exception as e:
    pass

@app.route('/', methods=['GET', 'POST'])
def login_page():
  global is_student
  if request.method == 'POST':
    if request.form.get('login'):
      username = request.form.get('username')
      input_password = request.form.get('password')
      is_student = True if request.form.get('roles')=='student' else False 
      if is_student:
        user = g.conn.execute("SELECT * FROM Students WHERE username='{}'".format(username))
      else:
        user = g.conn.execute("SELECT * FROM Instructors WHERE username='{}'".format(username))
      user = user.fetchone()
      if user==None:
        flash('username does not exist')
        return redirect(url_for('login_page'))
      user = User(user.username, is_student)
      if user.check_password(input_password):
        login_user(user)
        current_user.online = True
        flash('your are logged in')
        return redirect(url_for('main'))
      else:
        flash('Wrong password')
        return redirect(url_for('login_page'))
      
  return render_template("login.html")

@app.route('/logout')
def logout_page():
    current_user.online = False
    logout_user()
    flash('your are logged out')
    return redirect(url_for("login_page"))  


@app.route('/main', methods=['GET', 'POST'])
@login_required
def main():
  ########################################################
  #                        Student                       #
  ########################################################
  if current_user.is_student:
    # Gtting User
    user = g.conn.execute("SELECT * FROM Students WHERE id='{}'".format(current_user.get_id()))
    user = user.fetchone()
    # Getting all courses regitered by current user regardless of status with instructor information
    my_courses = g.conn.execute('''
    SELECT Courses.id, Courses.name, Courses.c_id, Courses.course_header, Courses.college,Courses.credit,
    Make_registration.status, Courses.id,Instructors.name as instructor_name
    FROM Students, Make_registration, Courses,Instructors,Instruct
    WHERE Students.id='{}' and Students.id=Make_registration.student_id 
    and Courses.id=Make_registration.course_id and Instruct.instructor_id=Instructors.id
    and Instruct.course_id=Courses.id
    '''.format(current_user.get_id()))
    my_courses = my_courses.fetchall()

    all_my_course_times = []
    for my_course in my_courses:
      my_course_times = g.conn.execute('''
      SELECT Section_occur.day_of_week, Section_occur.begin_hour, Section_occur.begin_minute,
      Section_occur.duration, Courses.course_header, Courses.c_id
      FROM Courses,Section_occur
      WHERE Courses.id={} and Section_occur.id=Courses.id
      '''.format(my_course[0]))
      my_course_times = my_course_times.fetchall()
      for my_course_time in my_course_times:
        all_my_course_times.append(my_course_time)
    all_my_course_times = sorted(all_my_course_times)

    if request.method == 'POST':
      # Getting Search results
      if request.form.get('search'):
        searchby = request.form.get('searchby')
        specifier = request.form.get('specifier')
        if searchby == 'header':
          filter_ = "Courses.course_header='{}'".format(specifier)
        elif searchby == 'ID':
          filter_ = "Courses.c_id LIKE '%%{}%%'".format(specifier)
        elif searchby == 'name':
          filter_ = "Courses.name LIKE '%%{}%%'".format(specifier)
        elif searchby == 'allCourses':
          filter_ = "Courses.name LIKE '%%{}%%'".format(specifier)

        courses = g.conn.execute('''
          SELECT * 
          FROM Courses,Instruct, Instructors,Use_classroom, Classrooms
          WHERE {} and Courses.id=Instruct.course_id and Instructors.id=Instruct.instructor_id 
          and Use_classroom.course_id=Courses.id and Classrooms.id=Use_classroom.classroom_id
          '''.format(filter_))
        courses = courses.fetchall()

        # Getting time periods and number of enrolled students accociated with each course
        all_time_periods = []
        enrolled_counts = []
        for course in courses:
          time_periods = g.conn.execute('''
          SELECT * 
          FROM Courses,Section_occur
          WHERE Courses.id={} and Section_occur.id=Courses.id
          '''.format(course[0]))
          time_periods = time_periods.fetchall()
          all_time_periods.append(time_periods)

          enrolled_count = g.conn.execute('''
          SELECT COUNT(*) 
          FROM Make_registration
          WHERE course_id={} and status='enrolled'
          '''.format(course[0]))
          enrolled_count = enrolled_count.fetchone()[0]
          enrolled_counts.append(enrolled_count)

        return render_template("student.html", user=user,courses=courses,my_courses=my_courses,
        all_time_periods=all_time_periods,enrolled_counts=enrolled_counts, search=True,
        all_my_course_times=all_my_course_times)

      # Making a registration
      if request.form.get('join_waitlist'):
        course_id = request.form.get('course_id')
        # Getting instructor id
        instructor_id = g.conn.execute('''
        select * 
        FROM Instruct 
        WHERE course_id={};
        '''.format(course_id))
        instructor_id = instructor_id.fetchone()[0]
        try:
          # insert to make registration
          g.conn.execute('''
          INSERT INTO 
          Make_registration 
          VALUES ({}, {}, CURRENT_TIMESTAMP, 'waitlist');
          '''.format(current_user.get_id(),course_id))
          # insert to manage registration
          g.conn.execute('''
          INSERT INTO 
          Manage_registration 
          VALUES ({},{}, {});
          '''.format(instructor_id,current_user.get_id(),course_id))
          flash('You have successfully joined the waitlist')
        except:
          flash('your already registered for this course')
        return redirect(url_for('main'))

      # Drop a Course
      if request.form.get('drop'):
        course_id = request.form.get('course_id')
        g.conn.execute('''
        DELETE 
        FROM Make_registration 
        WHERE student_id={} and course_id={};
        '''.format(current_user.get_id(),course_id))
        flash('you successfully dropped the course')
        return redirect(url_for('main'))
        
    return render_template("student.html", user=user,my_courses=my_courses,
    all_my_course_times=all_my_course_times)
  ########################################################
  #                        Instructor                    #
  ########################################################
  else:
    # Get all courses taught by current user
    courses_teach = g.conn.execute('''
          SELECT Courses.id, Courses.size, Courses.name, Courses.c_id, Courses.course_header, Instructors.name as instructor_name
          , Classrooms.building_name, Classrooms.room
          FROM Courses, Instruct, Instructors, Use_classroom, Classrooms
          WHERE Courses.id=Instruct.course_id and Instruct.instructor_id={} and 
          Instructors.id=Instruct.instructor_id and Use_classroom.course_id=Courses.id
          and Use_classroom.classroom_id=Classrooms.id 
          '''.format(current_user.get_id()))
    courses_teach = courses_teach.fetchall()
    # Get number of enrolled students associated with each course
    enrolled_counts = []
    all_time_periods = []
    for course in courses_teach:
      enrolled_count = g.conn.execute('''
      SELECT COUNT(*) 
      FROM Make_registration
      WHERE course_id={} and status='enrolled'
      '''.format(course[0]))
      enrolled_count = enrolled_count.fetchone()
      enrolled_counts.append(enrolled_count[0])

      time_periods = g.conn.execute('''
      SELECT * 
      FROM Courses,Section_occur
      WHERE Courses.id={} and Section_occur.id=Courses.id
      '''.format(course[0]))
      time_periods = time_periods.fetchall()
      all_time_periods.append(time_periods)


    # Get all registrations waiting to be considered
    waitlist_registrations = g.conn.execute('''
          SELECT Students.name, Students.college, Students.class_standing,Manage_registration.course_id
          ,Courses.course_header, Courses.c_id, Make_registration.status,Make_registration.registration_date,
          Make_registration.student_id
          FROM Manage_registration, Students, Courses, Make_registration
          WHERE Manage_registration.Instructor_id={} and Manage_registration.student_id=Students.id
          and Courses.id=Manage_registration.course_id and Make_registration.course_id=Courses.id
          and Make_registration.student_id=Students.id and Make_registration.status='waitlist'
          ORDER BY Make_registration.registration_date asc
          '''.format(current_user.get_id()))
    waitlist_registrations = waitlist_registrations.fetchall()
    # Get all approved registrations
    approved_registrations = g.conn.execute('''
          SELECT Students.name, Students.college, Students.class_standing,Manage_registration.course_id
          ,Courses.course_header, Courses.c_id, Make_registration.status,Make_registration.registration_date,
          Make_registration.student_id
          FROM Manage_registration, Students, Courses, Make_registration
          WHERE Manage_registration.Instructor_id={} and Manage_registration.student_id=Students.id
          and Courses.id=Manage_registration.course_id and Make_registration.course_id=Courses.id
          and Make_registration.student_id=Students.id and Make_registration.status='enrolled'
          ORDER BY Make_registration.registration_date asc
          '''.format(current_user.get_id()))
    approved_registrations = approved_registrations.fetchall()

    # Deny a registration request by deleting the record from Make_registration
    if request.form.get('deny'):
      course_id = request.form.get('course_id')
      student_id = request.form.get('student_id')
      g.conn.execute('''
        DELETE 
        FROM Make_registration 
        WHERE course_id={} and student_id={};
        '''.format(course_id,student_id))
      return redirect(url_for('main'))

    # Approve a registration request by updating status to 'enrolled'
    elif request.form.get('approve'):
      course_id = request.form.get('course_id')
      student_id = request.form.get('student_id')
      g.conn.execute('''
      UPDATE Make_registration
      SET status='enrolled'
      WHERE course_id={} and student_id={};
        '''.format(course_id,student_id))
      return redirect(url_for('main'))

    # expel a student by delteing record from make_registration
    elif request.form.get('expel'):
      course_id = request.form.get('course_id')
      student_id = request.form.get('student_id')
      g.conn.execute('''
        DELETE 
        FROM Make_registration 
        WHERE course_id={} and student_id={};
        '''.format(course_id,student_id))
      return redirect(url_for('main'))

    # Send a student back to waitlist by changing status to 'waitlist'
    elif request.form.get('back_to_waitlist'):
      course_id = request.form.get('course_id')
      student_id = request.form.get('student_id')
      g.conn.execute('''
      UPDATE Make_registration
      SET status='waitlist'
      WHERE course_id={} and student_id={};
        '''.format(course_id,student_id))
      return redirect(url_for('main'))

    return render_template("instructor.html",waitlist_registrations=waitlist_registrations,
    approved_registrations=approved_registrations,courses_teach=courses_teach,enrolled_counts=enrolled_counts,
    all_time_periods=all_time_periods)
