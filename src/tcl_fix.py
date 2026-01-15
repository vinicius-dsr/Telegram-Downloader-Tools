import os
import sys
import glob
import tkinter

def find_tcl_tk():
    """
    Attempts to locate Tcl/Tk libraries and set environment variables.
    """
    try:
        # Check if tkinter works already
        tkinter.Tk(useTk=0)
        print("Tkinter is already working.")
        return
    except Exception as e:
        print(f"Tkinter initial check failed: {e}")
        print("Attempting to locate Tcl/Tk libraries...")

    # Common paths to search for init.tcl
    search_paths = [
        os.path.join(sys.prefix, 'lib'),
        os.path.join(sys.base_prefix, 'lib'),
        '/usr/lib',
        '/usr/share',
        '/usr/local/lib',
        os.path.expanduser('~/.local/share'),
        os.path.expanduser('~/.local/lib'),
    ]

    tcl_lib = None
    tk_lib = None

    # Find init.tcl
    for path in search_paths:
        # Look for tcl8.*/init.tcl
        matches = glob.glob(os.path.join(path, '**/init.tcl'), recursive=True)
        if matches:
            # Sort by length to prefer shorter paths (usually root lib) or version
            matches.sort()
            tcl_init = matches[0]
            tcl_lib = os.path.dirname(tcl_init)
            print(f"Found Tcl library at: {tcl_lib}")
            break
    
    if tcl_lib:
        os.environ['TCL_LIBRARY'] = tcl_lib
        
        # Try to find matching Tk library
        # Usually in the same parent dir, named tk8.x
        parent = os.path.dirname(tcl_lib)
        tcl_dir_name = os.path.basename(tcl_lib) # e.g., tcl8.6
        version = tcl_dir_name.replace('tcl', '')
        
        tk_dir_name = f"tk{version}"
        possible_tk = os.path.join(parent, tk_dir_name)
        
        if os.path.exists(possible_tk):
            tk_lib = possible_tk
            print(f"Found Tk library at: {tk_lib}")
            os.environ['TK_LIBRARY'] = tk_lib
        else:
            # Fallback search for tk.tcl
            tk_matches = glob.glob(os.path.join(parent, '**/tk.tcl'), recursive=True)
            if tk_matches:
                tk_lib = os.path.dirname(tk_matches[0])
                print(f"Found Tk library at: {tk_lib}")
                os.environ['TK_LIBRARY'] = tk_lib

    if not tcl_lib:
        print("WARNING: Could not locate init.tcl. Please ensure Tcl/Tk is installed.")
        print("On Debian/Ubuntu: sudo apt install python3-tk tk-dev")
        print("On Fedora: sudo dnf install python3-tkinter tk-devel")
        print("On Arch Linux: sudo pacman -S tk")
    
    # Retry import/init to verify
    try:
        # We can't easily reload _tkinter, but setting env vars might help for subsequent calls
        # or if this function is called before the main app initializes root.
        pass
    except Exception:
        pass

if __name__ == "__main__":
    find_tcl_tk()
else:
    # Run automatically on import
    find_tcl_tk()
