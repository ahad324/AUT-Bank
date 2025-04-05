import os

# Change this extension if needed (e.g., ".log")
EXTENSION = ".txt"


def generate_structure(path, depth=0):
    structure = ""
    try:
        for item in sorted(os.listdir(path)):
            item_path = os.path.join(path, item)
            if os.path.isdir(item_path):
                structure += "│   " * depth + "├── " + item + "/\n"
                structure += generate_structure(item_path, depth + 1)
            else:
                structure += "│   " * depth + "├── " + item + "\n"
    except PermissionError:
        structure += "│   " * depth + "├── [Permission Denied]\n"

    return structure


def show_file_contents(path, file, output_file):
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().strip()
        if not content:
            return

        foldername, filename = os.path.split(path)
        foldername = foldername.replace(os.path.sep, "/")
        output_file.write(f"{foldername}/{filename}\n")
        output_file.write("<DOCUMENT>\n")
        output_file.write(content + "\n")
        output_file.write("</DOCUMENT>\n\n")
    except Exception as e:
        print(f"Error reading file {path}: {e}")


def show_directory_options(parent_dir):
    print(
        "Select a folder to generate the structure for or choose 'whole' for the entire directory:\n"
    )
    directories = [
        d for d in os.listdir(parent_dir) if os.path.isdir(os.path.join(parent_dir, d))
    ]

    print("[Whole] to generate structure for the entire directory")
    for i, folder in enumerate(directories):
        print(f"[{i+1}] {folder}")

    user_choice = input("\nEnter the number of your choice: ").strip()

    if user_choice.lower() == "whole":
        target_path = parent_dir
        print("\nGenerating structure for the entire directory...\n")
    elif user_choice.isdigit() and 1 <= int(user_choice) <= len(directories):
        target_path = os.path.join(parent_dir, directories[int(user_choice) - 1])
        print(
            f"\nGenerating structure for folder: {directories[int(user_choice) - 1]}\n"
        )
    else:
        print("Invalid choice. Exiting.")
        return

    structure = generate_structure(target_path)
    print(structure)

    # Ask for directory structure file name
    structure_filename = (
        input(
            f"\nEnter filename to save the directory structure (without extension): "
        ).strip()
        + EXTENSION
    )
    try:
        with open(structure_filename, "w", encoding="utf-8") as f:
            f.write("Directory Structure:\n\n")
            f.write(structure)
        print(f"\nDirectory structure saved to {structure_filename}")
    except Exception as e:
        print(f"Error writing directory structure file: {e}")

    # Ask if user wants to save file contents
    user_response = (
        input("Do you want to include file contents as well? (y/n): ").strip().lower()
    )
    if user_response == "y":
        content_filename = (
            input(f"Enter filename to save file contents (without extension): ").strip()
            + EXTENSION
        )
        try:
            with open(content_filename, "w", encoding="utf-8") as output_file:
                for root, dirs, files in os.walk(target_path):
                    for file in files:
                        if file == "__init__.py":
                            continue
                        file_path = os.path.join(root, file)
                        show_file_contents(file_path, file, output_file)
            print(f"\nFile contents saved to {content_filename}")
        except Exception as e:
            print(f"Error writing file contents: {e}")


if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    show_directory_options(script_dir)
