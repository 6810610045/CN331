from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.views import redirect_to_login
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import EditTopicForm, TopicForm
from .models import Comment, Side, Topic


def topic_list(request):
    search_query = request.GET.get("q", "")
    if search_query:
        topics = Topic.objects.filter(
            Q(title__icontains=search_query) | Q(description__icontains=search_query)
        ).distinct()
    else:
        topics = Topic.objects.all()

    return render(
        request,
        "debates/topic_list.html",
        {"topics": topics, "search_query": search_query},
    )


def topic_detail(request, topic_id):
    topic = get_object_or_404(Topic, id=topic_id)
    user_vote = None
    if request.user.is_authenticated:
        user_vote = topic.comments.filter(
            author=request.user, side__isnull=False
        ).first()

    if request.method == "POST":
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())

        if topic.is_expired():
            messages.error(request, "กระทู้นี้ปิดรับโหวตแล้ว")
            return redirect("topic_detail", topic_id=topic.id)

        if user_vote:
            messages.info(request, "คุณได้ลงคะแนนในกระทู้นี้แล้ว")
            return redirect("topic_detail", topic_id=topic.id)

        side_id = request.POST.get("side")
        comment_text = request.POST.get("comment_text", "").strip()

        if not side_id or not comment_text:
            messages.error(request, "กรุณาเลือกฝั่งและเขียนความคิดเห็นก่อนส่ง")
            return redirect("topic_detail", topic_id=topic.id)

        try:
            selected_side = Side.objects.get(id=side_id, topic=topic)
        except (Side.DoesNotExist, TypeError, ValueError):
            messages.error(request, "ตัวเลือกนี้ไม่ถูกต้อง กรุณาเลือกฝั่งในกระทู้นี้")
            return redirect("topic_detail", topic_id=topic.id)

        Comment.objects.create(
            topic=topic, author=request.user, side=selected_side, text=comment_text
        )
        messages.success(request, "บันทึกคะแนนและความคิดเห็นแล้ว")
        return redirect("topic_detail", topic_id=topic.id)

    return render(
        request,
        "debates/topic_detail.html",
        {"topic": topic, "user_vote": user_vote},
    )


def signup(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("topic_list")
    else:
        form = UserCreationForm()
    return render(request, "debates/signup.html", {"form": form})


@login_required
def create_topic(request):
    if request.method == "POST":
        form = TopicForm(request.POST)
        sides = request.POST.getlist("sides")
        if form.is_valid():
            topic = form.save(commit=False)
            topic.created_by = request.user
            topic.save()
            for side_name in sides:
                if side_name.strip():
                    Side.objects.create(topic=topic, name=side_name.strip())
            return redirect("topic_list")
    else:
        form = TopicForm()

    return render(request, "debates/create_topic.html", {"form": form})


@login_required
def delete_topic(request, topic_id):
    topic = get_object_or_404(Topic, id=topic_id)
    if request.user == topic.created_by:
        topic.delete()
    return redirect("topic_list")


@login_required
def edit_topic(request, topic_id):
    topic = get_object_or_404(Topic, id=topic_id)

    if request.user != topic.created_by:
        return redirect("topic_list")

    if request.method == "POST":
        form = EditTopicForm(request.POST, instance=topic)
        if form.is_valid():
            form.save()
            return redirect("topic_detail", topic_id=topic.id)
    else:
        form = EditTopicForm(instance=topic)

    return render(request, "debates/edit_topic.html", {"form": form, "topic": topic})


@login_required
def user_profile(request):
    my_topics = Topic.objects.filter(created_by=request.user).order_by("-created_at")
    my_comments = Comment.objects.filter(author=request.user).order_by("-created_at")

    return render(
        request,
        "debates/profile.html",
        {"my_topics": my_topics, "my_comments": my_comments},
    )