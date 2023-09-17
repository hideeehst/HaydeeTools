"""
build the project locally
"""

import os
import zipfile
from pathlib import Path
import shutil

BLENDER_VERSION_STR="3.3"

def match_path(path, patterns):
    """ match a pattern """
    for pattern in patterns:
        if pattern in str(path):
            return True
    return False


def get_gitignore_entries(project_dir:str):
    """ get gitignore entries """
    ignored_patterns = []
    gitignore_path=Path(project_dir).joinpath(".gitignore")

    if not gitignore_path.exists():
        return ignored_patterns

    with open(project_dir.joinpath(".gitignore")) as f:
        for line in f:
            line=line.strip()
            empty_line=line==""
            invalid_line=any(line.startswith(x) for x in ["#","!"])
            if not (empty_line or invalid_line):
                ignored_patterns.append(line)

    return ignored_patterns

def clear_build_folder(project_dir:str):
    """ clear the build folder """
    if not Path(project_dir).exists():
        return

    build_dir=Path(project_dir).joinpath("build")
    for file in build_dir.glob("*"):
        if file.is_file():
            file.unlink()
        else:
            shutil.rmtree(file,ignore_errors=True)

    build_dir.mkdir(parents=True,exist_ok=True)

def make_archive(project_dir:str,ignored_patterns:list,):
    """ make archive """
    project_name=Path(project_dir).name
    final_zip_path = Path(project_dir).joinpath("build").joinpath(
        project_name + ".zip")

    #make archive
    with zipfile.ZipFile(str(final_zip_path), "w") as zfile:
        for file in project_dir.rglob("*"):
            relative_path=file.relative_to(project_dir)

            #skip gitignore patterns
            if match_path(relative_path,ignored_patterns):
                continue

            if file.is_file():
                print(f"Adding {relative_path} ...")
                zfile.write(str(file), arcname=project_name+"/"+str(relative_path))

print("Project has been packaged.")

def copy_to_blender_addons(project_dir:str,blender_version=BLENDER_VERSION_STR):
    """ copy to blender addons folder """
    print("Copying to blender addons folder...")
    project_name=Path(project_dir).name
    blender_addons_folder=Path(os.getenv('APPDATA')).joinpath(rf"Blender Foundation\Blender\{blender_version}\scripts\addons")
    haydeetools_addons_folder=blender_addons_folder.joinpath(project_name)

    final_zip_path = Path(project_dir).joinpath("build").joinpath(
        project_name + ".zip")
    #clear project-addon in addons folder
    dst_folder=blender_addons_folder.joinpath(project_name)
    if dst_folder.exists():
        items_in_dst_folder=list(dst_folder.glob("*"))

        print(f"Clearing Addon in Blender {blender_version} addons ...")
        if len(items_in_dst_folder)>0:
            for item in items_in_dst_folder:
                if item.is_file():
                    item.unlink()
                else:
                    shutil.rmtree(item)

    print("Creating Addon in Blender addons ...")
    dst_folder.mkdir(parents=True,exist_ok=True)
    zipfile.ZipFile(final_zip_path).extractall(haydeetools_addons_folder)


def build():
    # project dir,assuming this script is located in Project/scripts/
    project_dir=Path(__file__).parent.parent
    ignored_patterns=[".git", ".vscode", "build", "build.py", "__pycache__"]
    ignored_patterns+=get_gitignore_entries(project_dir)

    clear_build_folder(project_dir)
    make_archive(project_dir,ignored_patterns)
    copy_to_blender_addons(project_dir)

    print("Done.")



build()
