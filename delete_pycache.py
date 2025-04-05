import os
import shutil

def delete_pycache(directory):
    for root, dirs, files in os.walk(directory):
        if "__pycache__" in dirs:
            pycache_path = os.path.join(root, "__pycache__")
            shutil.rmtree(pycache_path)
            print(f"Deleted: {pycache_path}")

if __name__ == "__main__":
    project_dir = os.getcwd()  # Get the current working directory
    delete_pycache(project_dir)
    print("All __pycache__ folders deleted successfully!")
