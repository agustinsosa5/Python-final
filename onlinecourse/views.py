from django.shortcuts import render
from django.http import HttpResponseRedirect
# <HINT> Import any new Models here
from .models import Course, Enrollment, Submission, Choice, Question
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.views import generic
from django.contrib.auth import login, logout, authenticate
import logging
# Get an instance of a logger
logger = logging.getLogger(__name__)
# Create your views here.

def registration_request(request):
    context = {}
    if request.method == 'GET':
        return render(request, 'onlinecourse/user_registration_bootstrap.html', context)
    elif request.method == 'POST':
        # Check if user exists
        username = request.POST['username']
        password = request.POST['psw']
        first_name = request.POST['firstname']
        last_name = request.POST['lastname']
        user_exist = False
        try:
            User.objects.get(username=username)
            user_exist = True
        except:
            logger.error("New user")
        if not user_exist:
            user = User.objects.create_user(username=username, first_name=first_name, last_name=last_name,
                                            password=password)
            login(request, user)
            return redirect("onlinecourse:index")
        else:
            context['message'] = "User already exists."
            return render(request, 'onlinecourse/user_registration_bootstrap.html', context)


def login_request(request):
    context = {}
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['psw']
        user = authenticate(username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('onlinecourse:index')
        else:
            context['message'] = "Invalid username or password."
            return render(request, 'onlinecourse/user_login_bootstrap.html', context)
    else:
        return render(request, 'onlinecourse/user_login_bootstrap.html', context)


def logout_request(request):
    logout(request)
    return redirect('onlinecourse:index')


def check_if_enrolled(user, course):
    is_enrolled = False
    if user.id is not None:
        # Check if user enrolled
        num_results = Enrollment.objects.filter(user=user, course=course).count()
        if num_results > 0:
            is_enrolled = True
    return is_enrolled


# CourseListView
class CourseListView(generic.ListView):
    template_name = 'onlinecourse/course_list_bootstrap.html'
    context_object_name = 'course_list'

    def get_queryset(self):
        user = self.request.user
        courses = Course.objects.order_by('-total_enrollment')[:10]
        for course in courses:
            if user.is_authenticated:
                course.is_enrolled = check_if_enrolled(user, course)
        return courses


class CourseDetailView(generic.DetailView):
    model = Course
    template_name = 'onlinecourse/course_detail_bootstrap.html'


def enroll(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    user = request.user

    is_enrolled = check_if_enrolled(user, course)
    if not is_enrolled and user.is_authenticated:
        # Create an enrollment
        Enrollment.objects.create(user=user, course=course, mode='honor')
        course.total_enrollment += 1
        course.save()

    return HttpResponseRedirect(reverse(viewname='onlinecourse:course_details', args=(course.id,)))


def submit(request, course_id):
    # Obtener el usuario y el objeto del curso
    user = request.user
    course = get_object_or_404(Course, pk=course_id)

    # Obtener la inscripción asociada al usuario y al curso
    enrollment = Enrollment.objects.get(user=user, course=course)

    if request.method == 'POST':
        # Crear un objeto de envío de examen relacionado con la inscripción
        submission = Submission.objects.create(enrollment=enrollment)

        # Recopilar las opciones seleccionadas del formulario del examen
        selected_choices = extract_answers(request)

        # Obtener los objetos Choice según los IDs seleccionados
        choices = Choice.objects.filter(id__in=selected_choices)

        # Agregar cada opción seleccionada al objeto de envío
        submission.choices.set(choices)

        # Redirigir a la vista de resultados del examen con el ID de envío
        return redirect('onlinecourse:show_exam_result', course_id=course.id, submission_id=submission.id)

    # Si no se realizó una solicitud POST, renderizar el formulario del examen
    return render(request, 'onlinecourse/exam_submission.html', {'course': course})


def extract_answers(request):
    submitted_answers = []
    for key in request.POST:
        if key.startswith('choice'):
            value = request.POST[key]
            choice_id = int(value)
            submitted_answers.append(choice_id)
    return submitted_answers


def show_exam_result(request, course_id, submission_id):
    # Obtener el curso y el envío según sus IDs
    course = get_object_or_404(Course, pk=course_id)
    submission = get_object_or_404(Submission, pk=submission_id)

    # Obtener los IDs de las opciones seleccionadas del registro de envío
    selected_choices_ids = submission.choices.values_list('id', flat=True)

    # Obtener todas las preguntas del curso
    questions = Question.objects.filter(course=course)

    # Calcular el puntaje total y verificar si el estudiante aprobó el examen
    total_score = 0
    for question in questions:
        if question.is_get_score(selected_choices_ids):
            total_score += question.grade_point

    # Renderizar la vista de resultados del examen con los datos necesarios
    return render(request, 'onlinecourse/exam_result_bootstrap.html', {'course': course, 'submission': submission, 'total_score': total_score})



