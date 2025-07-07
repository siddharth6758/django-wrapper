import os
import subprocess
import sys
import time
import re
import venv

def create_virtualenv(project_name, venv_name="venv"):
    venv_path = os.path.join(project_name, venv_name)
    os.makedirs(project_name, exist_ok=True)
    print(f"📦 Creating virtual environment at {venv_path}...")
    venv.create(venv_path, with_pip=True)
    return os.path.abspath(venv_path)

def install_requirements(venv_dir):
    pip_path = os.path.join(venv_dir, "bin", "pip") if os.name != 'nt' else os.path.join(venv_dir, "Scripts", "pip.exe")
    subprocess.run([pip_path, "install", "django"], check=True)

def run_in_venv(venv_dir, args):
    python_path = os.path.join(venv_dir, "bin", "python") if os.name != 'nt' else os.path.join(venv_dir, "Scripts", "python.exe")
    subprocess.run([python_path] + args, check=True)

def start_project(venv_dir, project_name):
    django_admin = os.path.join(venv_dir, "bin", "django-admin") if os.name != 'nt' else os.path.join(venv_dir, "Scripts", "django-admin.exe")
    os.makedirs(project_name, exist_ok=True)
    cwd = os.getcwd()
    os.chdir(project_name)
    subprocess.run([django_admin, "startproject", project_name, "."], check=True)
    os.chdir(cwd)

def start_app(venv_dir, app_name, project_dir):
    os.chdir(project_dir)
    run_in_venv(venv_dir, ["manage.py", "startapp", app_name])

    app_dir = os.path.join(os.getcwd(), app_name)

    for _ in range(10):
        if os.path.isdir(app_dir):
            break
        time.sleep(0.1)
    else:
        raise FileNotFoundError(f"App directory {app_dir} was not created.")

    create_app_urls(app_dir)
    os.chdir("..")


def create_app_urls(app_dir):
    urls_path = os.path.join(app_dir, "urls.py")
    if not os.path.exists(urls_path):
        with open(urls_path, "w") as f:
            f.write(
                "from django.urls import path\n\n"
                "urlpatterns = []\n"
            )

def include_app_urls_in_project(app_name, project_urls_path):
    with open(project_urls_path, "r") as f:
        content = f.read()

    updated = False

    if "from django.urls import path, include" not in content:
        if "from django.urls import path" in content:
            content = content.replace(
                "from django.urls import path",
                "from django.urls import path, include"
            )
        elif "from django.urls import" in content:
            content = re.sub(
                r"from django\.urls import (.+)",
                r"from django.urls import \1, include",
                content
            )
        else:
            content = "from django.urls import path, include\n" + content

        updated = True

    include_line = f"path('', include('{app_name}.urls'))"
    if include_line not in content:
        if "urlpatterns = [" in content:
            content = content.replace(
                "urlpatterns = [",
                f"urlpatterns = [\n    {include_line},"
            )
            updated = True

    if updated:
        with open(project_urls_path, "w") as f:
            f.write(content)


def configure_settings(app_name, settings_path, use_templates_and_static):
    with open(settings_path, "r") as f:
        content = f.read()

    updated = False

    # Add 'import os' if it's not present
    if "import os" not in content:
        content = "import os\n" + content
        updated = True

    # Add BASE_DIR if it's not present
    if "BASE_DIR = " not in content:
        base_dir_line = "BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))\n"
        content = content.replace("import os", f"import os\n{base_dir_line}")
        updated = True

    # Add the app to INSTALLED_APPS if it's not already there
    if app_name not in content:
        installed_apps_index = content.find("INSTALLED_APPS = [")
        if installed_apps_index != -1:
            before_apps = content[:installed_apps_index]
            after_apps = content[installed_apps_index:]
            
            # Ensure app name is added to INSTALLED_APPS
            after_apps = after_apps.replace(
                "INSTALLED_APPS = [",
                f"INSTALLED_APPS = [\n    '{app_name}',"
            )
            content = before_apps + after_apps
            updated = True
        else:
            # In case INSTALLED_APPS doesn't exist (very unlikely)
            content += f"\nINSTALLED_APPS = [\n    '{app_name}',\n]\n"
            updated = True

    if use_templates_and_static:
        # Add template and static setup if required
        def update_templates_dirs_block(content):
            pattern = r"'DIRS'\s*:\s*\[(.*?)\]"
            match = re.search(pattern, content, re.DOTALL)
            if match and "os.path.join(BASE_DIR, 'templates')" not in match.group(0):
                new_dirs = "'DIRS': [os.path.join(BASE_DIR, 'templates')]"
                return re.sub(pattern, new_dirs, content, count=1), True
            return content, False

        content, changed = update_templates_dirs_block(content)
        updated = updated or changed

        if "STATICFILES_DIRS" not in content:
            content += "\nSTATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]\n"
            updated = True

        if "STATIC_URL" not in content:
            content += "\nSTATIC_URL = '/static/'\n"
            updated = True

        if "STATIC_ROOT" not in content:
            content += "\nSTATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')\n"
            updated = True

    if updated:
        with open(settings_path, "w") as f:
            f.write(content)


def create_global_static_and_template_dirs(project_dir):
    static_dir = os.path.join(project_dir, "static")
    templates_dir = os.path.join(project_dir, "templates")
    os.makedirs(static_dir, exist_ok=True)
    os.makedirs(templates_dir, exist_ok=True)
    index_html = os.path.join(templates_dir, "index.html")
    if not os.path.exists(index_html):
        with open(index_html, "w") as f:
            f.write("<h1>Welcome to your Django project!</h1>\n")

def update_urls_for_static(project_name):
    urls_path = os.path.join(project_name, project_name, "urls.py")
    with open(urls_path, "r") as f:
        content = f.read()
    if "static(settings.STATIC_URL" not in content:
        static_config = (
            "\nfrom django.conf import settings\n"
            "from django.conf.urls.static import static\n"
            "\nurlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)\n"
        )
        with open(urls_path, "a") as f:
            f.write(static_config)

def run_migrations(venv_dir, project_dir):
    os.chdir(project_dir)
    run_in_venv(venv_dir, ["manage.py", "makemigrations"])
    run_in_venv(venv_dir, ["manage.py", "migrate"])
    os.chdir("..")

def bootstrap(project_name, venv_name, app_names, use_templates_and_static):
    venv_path = create_virtualenv(project_name, venv_name)
    install_requirements(venv_path)
    print(f"🚀 Creating Django project: {project_name}")
    start_project(venv_path, project_name)

    if use_templates_and_static:
        create_global_static_and_template_dirs(project_name)

    settings_path = os.path.join(project_name, project_name, "settings.py")
    project_urls_path = os.path.join(project_name, project_name, "urls.py")

    for app_name in app_names:
        print(f"📂 Creating app: {app_name}")
        start_app(venv_path, app_name, project_name)
        configure_settings(app_name, settings_path, use_templates_and_static)
        include_app_urls_in_project(app_name, project_urls_path)

    print("🛠 Running migrations...")
    run_migrations(venv_path, project_name)

    if use_templates_and_static:
        update_urls_for_static(project_name)

    print(f"✅ Done! Django project '{project_name}' with apps {app_names} created in virtual environment '{venv_name}'.")

def main():
    print("👋 Welcome to the Django Bootstrapper!")
    venv_name = input("* Enter virtual environment name (default: venv): ").strip() or "venv"
    project_name = input("* Enter Django project name: ").strip()

    app_names = []
    print("* Enter Django app names (enter 0 to stop):")
    while True:
        app = input("  - App name: ").strip()
        if app == "0":
            break
        if app:
            app_names.append(app)

    static_template_choice = input("* Do you want to add template/static file setup? (y/n): ").strip().lower()
    use_templates_and_static = static_template_choice in ("y", "yes")

    bootstrap(project_name, venv_name, app_names, use_templates_and_static)

if __name__ == "__main__":
    main()

