from skills import views as skills_views


def skill_graph(request):
    return skills_views.skills_list(request)


def edit_skills(request):
    return skills_views.skills_edit(request)
