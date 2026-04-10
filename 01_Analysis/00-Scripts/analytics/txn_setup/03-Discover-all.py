# Discover all files in the client folder
all_files = list(CLIENT_PATH.glob(f'**/*.{FILE_EXTENSION}'))
print(f"Found {len(all_files)} files:\n")
for file in sorted(all_files):
    file_size = file.stat().st_size / 1024  # Size in KB
    print(f"  • {file.name} ({file_size:.1f} KB)")

# Identify file extensions
extensions = set([f.suffix.lower() for f in all_files if f.is_file()])
print(f"\nFile types found: {extensions}")
