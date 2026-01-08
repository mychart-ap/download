import os
import re

# --- CONFIGURATION ---
# Extensions of files to process
TARGET_EXTENSIONS = ['.html']

# 1. Text replacement (Domain)
OLD_DOMAIN = "mychart-app.com"
NEW_DOMAIN = "mychart-ap.github.io/download/"

# 2. Path prefix to add to relative paths starting with /
# Example: /images/logo.png -> /download/images/logo.png
PATH_PREFIX = "/download"

# 3. Fix missing .html extension in links
# Checks if a link like /blog/news points to a file /blog/news.html and updates the link.
FIX_MISSING_HTML_EXTENSION = True

# Extra replacements (typos, etc.)
EXTRA_REPLACEMENTS = []
# ---------------------

def process_content(content, root_dir):
    # 1. Simple string replacement for the domain
    content = content.replace(OLD_DOMAIN, NEW_DOMAIN)
    

    # 2. Regex replacement for relative paths
    # We want to match attributes like href="/...", src="/...", etc.
    # and CSS styles like url('/...')
    
    # Helper to prepend prefix if not present
    def replace_callback(match):
        full_match = match.group(0)
        prefix_part = match.group(1) # e.g. href="
        quote = match.group(2)       # " or '
        path = match.group(3)        # /some/path
        
        # Skip protocol-relative URLs (starting with //)
        if path.startswith('//'):
            return full_match
            
        # Skip if already starts with the target prefix
        # We check both "/download" and "/download/" to be safe
        if path.startswith(PATH_PREFIX) or path.startswith(PATH_PREFIX.rstrip('/') + '/'):
             return full_match

        # Construct new path
        # Ensure we don't get double slashes if PATH_PREFIX ends with / and path starts with /
        clean_prefix = PATH_PREFIX.rstrip('/')
        new_path = clean_prefix + path
        
        return f"{prefix_part}{quote}{new_path}{quote}"

    # Regex for HTML attributes
    # Matches: (href=|src=|action=|content=|data-src=|srcset=)\s*(["\'])(/.*?)\2
    # We look for paths starting with /
    html_pattern = re.compile(r'(href=|src=|action=|content=|data-src=|srcset=)\s*(["\'])(/.*?)\2', re.IGNORECASE)
    content = html_pattern.sub(replace_callback, content)

    # Regex for CSS url()
    # Matches: url( ("|'|) (/...) ("|'|) )
    # Note: This is a bit simplified. It handles url('/path') and url(/path)
    def css_callback(match):
        full_match = match.group(0)
        start_url = match.group(1) # url(
        quote = match.group(2)     # ' or " or empty
        path = match.group(3)      # /path
        end_quote = match.group(4) # ' or " or empty
        end_url = match.group(5)   # )

        if path.startswith('//'):
            return full_match
            
        if path.startswith(PATH_PREFIX):
             return full_match

        clean_prefix = PATH_PREFIX.rstrip('/')
        new_path = clean_prefix + path
        
        return f"{start_url}{quote}{new_path}{end_quote}{end_url}"

    css_pattern = re.compile(r'(url\(\s*)([\'"]?)(/.*?)([\'"]?)(\s*\))', re.IGNORECASE)
    content = css_pattern.sub(css_callback, content)

    # 3. Fix links to .html files
    if FIX_MISSING_HTML_EXTENSION:
        def fix_html_link(match):
            full_match = match.group(0)
            quote = match.group(1)
            url = match.group(2)
            
            if not url.startswith(PATH_PREFIX):
                return full_match
            
            # Strip prefix
            rel_path = url[len(PATH_PREFIX):]
            clean_path = rel_path.split('?')[0].split('#')[0]
            
            if clean_path.startswith('/'):
                clean_path = clean_path.lstrip('/')
            if clean_path.endswith('/'):
                clean_path = clean_path.rstrip('/')
                
            if not clean_path: 
                return full_match

            potential_file_path = os.path.join(root_dir, clean_path.replace('/', os.sep))
            
            if os.path.isdir(potential_file_path):
                return full_match

            potential_html = potential_file_path + ".html"
            if os.path.isfile(potential_html):
                url_base = url.split('?')[0].split('#')[0]
                if url_base.endswith('/'):
                    url_base = url_base[:-1]
                
                suffix = ""
                if '?' in url:
                    suffix += '?' + url.split('?', 1)[1]
                elif '#' in url:
                    suffix += '#' + url.split('#', 1)[1]
                    
                new_url = url_base + ".html" + suffix
                return f'href={quote}{new_url}{quote}'
            
            return full_match

        content = re.sub(r'href=(["\'])(.*?)\1', fix_html_link, content)

    return content

def main():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    print(f"Starting processing in: {root_dir}")
    print(f"Target extensions: {TARGET_EXTENSIONS}")
    print(f"Replacing '{OLD_DOMAIN}' with '{NEW_DOMAIN}'")
    print(f"Fixing typos: {EXTRA_REPLACEMENTS}")
    print(f"Prefixing root-relative paths with '{PATH_PREFIX}'")
    if FIX_MISSING_HTML_EXTENSION:
        print("Fixing missing .html extensions in internal links")

    processed_count = 0
    modified_count = 0

    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if any(file.lower().endswith(ext) for ext in TARGET_EXTENSIONS):
                filepath = os.path.join(root, file)
                processed_count += 1
                
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    new_content = process_content(content, root_dir)
                    
                    if new_content != content:
                        with open(filepath, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        print(f"[MODIFIED] {filepath}")
                        modified_count += 1
                    # else:
                    #     print(f"[SKIPPED]  {filepath}")
                        
                except Exception as e:
                    print(f"[ERROR] Could not process {filepath}: {e}")

    print(f"\nDone. Scanned {processed_count} files. Modified {modified_count} files.")

if __name__ == "__main__":
    main()

