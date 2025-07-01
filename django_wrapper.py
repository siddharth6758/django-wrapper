import os
import subprocess
import sys
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
    os.chdir("..")

def configure_settings(app_name, settings_path):
    with open(settings_path, "r") as f:
        content = f.read()

    updated = False

    # Add app to INSTALLED_APPS
    if app_name not in content:
        content = content.replace(
            "INSTALLED_APPS = [",
            f"INSTALLED_APPS = [\n    '{app_name}',"
        )
        updated = True

    # Add TEMPLATES['DIRS']
    if "'DIRS': []" in content:
        content = content.replace(
            "'DIRS': []",
            "'DIRS': [os.path.join(BASE_DIR, 'templates')]"
        )
        updated = True

    # Add STATICFILES_DIRS
    if "STATICFILES_DIRS" not in content:
        content += "\nSTATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]\n"
        updated = True

    # Add STATIC_URL if not defined
    if "STATIC_URL" not in content:
        content += "\nSTATIC_URL = '/static/'\n"
        updated = True

    if "STATIC_ROOT" not in content:
        content += "\nSTATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')\n"
        updated = True

    if updated:
        # Ensure import os and BASE_DIR are present
        if "import os" not in content:
            content = "import os\n" + content

        if "BASE_DIR = " not in content:
            base_dir_line = "BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))\n"
            content = content.replace("import os", f"import os\n{base_dir_line}")

        with open(settings_path, "w") as f:
            f.write(content)

def create_global_static_and_template_dirs(project_dir):
    static_dir = os.path.join(project_dir, "static")
    templates_dir = os.path.join(project_dir, "templates")

    os.makedirs(static_dir, exist_ok=True)
    os.makedirs(templates_dir, exist_ok=True)

    # Create a default index.html in templates
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

def bootstrap(project_name, app_names):
    # venv_dir = "venv"
    venv_path = create_virtualenv(project_name)
    install_requirements(venv_path)

    print(f"🚀 Creating Django project: {project_name}")
    start_project(venv_path, project_name)

    create_global_static_and_template_dirs(project_name)

    settings_path = os.path.join(project_name, project_name, "settings.py")

    for app_name in app_names:
        print(f"📂 Creating app: {app_name}")
        start_app(venv_path, app_name, project_name)
        configure_settings(app_name, settings_path)

    print("🛠 Running migrations...")
    run_migrations(venv_path, project_name)
    update_urls_for_static(project_name)

    print(f"✅ Done! Django project '{project_name}' with apps {app_names} created in virtual environment.")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Create Django project and apps inside virtualenv.")
    parser.add_argument("project", help="Project name")
    parser.add_argument("apps", nargs="+", help="One or more app names")
    args = parser.parse_args()
    bootstrap(args.project, args.apps)

if __name__ == "__main__":
    main()

