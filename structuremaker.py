import os

def generate_structure(path, depth=0):
    """
    Generates a formatted directory structure starting from the given path.
    
    Args:
        path (str): Directory path to start generating structure.
        depth (int): The current depth of recursion (used for indentation).
        
    Returns:
        str: A formatted string representing the directory structure.
    """
    structure = ""
    try:
        # List all files and directories in the current directory
        for item in sorted(os.listdir(path)):
            item_path = os.path.join(path, item)
            if os.path.isdir(item_path):
                structure += "│   " * depth + "├── " + item + "/\n"
                structure += generate_structure(item_path, depth + 1)
            else:
                structure += "│   " * depth + "├── " + item + "\n"
    except PermissionError:
        # In case of permission errors
        structure += "│   " * depth + "├── [Permission Denied]\n"
    
    return structure

def show_file_contents(path, file, output_file):
    """
    Displays the content of a file in a structured format and writes it to the output file.
    
    Args:
        path (str): Path of the file's directory.
        file (str): Filename.
        output_file (file object): Output file to write the content.
    """
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read().strip()  # Strip leading/trailing whitespaces to handle empty files
        if not content:  # Skip empty files
            return

        foldername, filename = os.path.split(path)
        foldername = foldername.replace(os.path.sep, '/')
        output_file.write(f"{foldername}/{filename}\n")
        output_file.write("<DOCUMENT>\n")
        output_file.write(content + "\n")
        output_file.write("</DOCUMENT>\n\n")
    except Exception as e:
        print(f"Error reading file {path}: {e}")

def show_directory_options(parent_dir):
    """
    Show the user available folders within the directory.
    
    Args:
        parent_dir (str): The parent directory where the script is located.
    """
    print("Select a folder to generate the structure for or choose 'whole' for the entire directory:\n")
    
    # List all directories at the same level as the script
    directories = [d for d in os.listdir(parent_dir) if os.path.isdir(os.path.join(parent_dir, d))]
    
    print("[Whole] to generate structure for the entire directory")
    
    for i, folder in enumerate(directories):
        print(f"[{i+1}] {folder}")
    
    user_choice = input("\nEnter the number of your choice: ").strip()
    
    # Handle user selection
    if user_choice.lower() == 'whole':
        print(f"\nGenerating structure for the entire directory...\n")
        full_structure = generate_structure(parent_dir)
        print(full_structure)
        show_file_contents_option(full_structure, parent_dir)
    elif user_choice.isdigit() and 1 <= int(user_choice) <= len(directories):
        folder_choice = directories[int(user_choice) - 1]
        print(f"\nGenerating structure for folder: {folder_choice}\n")
        folder_path = os.path.join(parent_dir, folder_choice)
        folder_structure = generate_structure(folder_path)
        print(folder_structure)
        show_file_contents_option(folder_structure, folder_path)
    else:
        print("Invalid choice. Exiting.")

def show_file_contents_option(structure, parent_dir):
    """
    Asks the user if they want to see the file content for each file in the structure.
    
    Args:
        structure (str): The structure of the folder.
        parent_dir (str): Path of the directory to check the files in.
    """
    user_response = input("Do you want to see the content of the files? (y/n): ").strip().lower()
    
    if user_response == 'y':
        # Ask for output filename
        output_filename = input("Enter the filename to save the content (e.g., output.txt): ").strip()
        
        try:
            with open(output_filename, 'w', encoding='utf-8') as output_file:
                output_file.write("Directory Structure and File Contents:\n\n")
                
                # Process files in all subdirectories and write their content to the output file
                for root, dirs, files in os.walk(parent_dir):
                    for file in files:
                        if file == '__init__.py':  # Skip __init__.py files
                            continue
                        file_path = os.path.join(root, file)
                        show_file_contents(file_path, file, output_file)
                print(f"\nFile contents have been saved to {output_filename}")
        
        except Exception as e:
            print(f"Error writing to file {output_filename}: {e}")

if __name__ == "__main__":
    # Get the path where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    show_directory_options(script_dir)
