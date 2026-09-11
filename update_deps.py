import subprocess
import requests
import sys
import re
import tomllib

def get_latest_version(package_name):
    """Fetch the latest version from PyPI."""
    url = f"https://pypi.org/pypi/{package_name}/json"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        return data["info"]["version"]
    except requests.RequestException as e:
        print(f"Error fetching {package_name}: {e}")
        return None

def run_uv_add(args):
    """Run uv add command and refresh cache on failure once."""
    result = subprocess.run(["uv", "add"] + args)
    if result.returncode == 0:
        return True

    print("Initial add failed, attempting to refresh cache and retry...")

    # Refresh cache
    subprocess.run(["uv", "cache", "clean"], check=False)

    # Retry once
    result = subprocess.run(["uv", "add"] + args)
    return result.returncode == 0


def normalize_name(name):
    """Normalize a package name to compare/match dependencies consistently."""
    return re.sub(r"[-_.]+", "-", name).lower()


def get_optional_groups(package_name):
    """Find all optional dependency groups in pyproject.toml that include the package name."""
    normalized_target = normalize_name(package_name)
    groups = []
    try:
        with open("pyproject.toml", "rb") as f:
            data = tomllib.load(f)
        optional_deps = data.get("project", {}).get("optional-dependencies", {})
        for group, reqs in optional_deps.items():
            for req in reqs:
                # Match the package name at the start of the requirement string
                match = re.match(r'^([A-Za-z0-9]([A-Za-z0-9._-]*[A-Za-z0-9])?)', req)
                if match:
                    req_name = match.group(1)
                    if normalize_name(req_name) == normalized_target:
                        groups.append(group)
                        break
    except Exception as e:
        print(f"Warning: could not parse pyproject.toml to find optional dependencies: {e}")
    return groups


def update_optional_dependencies(package_name, version):
    """Update the package in any optional dependency groups it belongs to."""
    groups = get_optional_groups(package_name)
    for group in groups:
        print(f"Adding {package_name}>={version} to optional group '{group}'...")
        success = run_uv_add(["--optional", group, f"{package_name}>={version}"])
        if not success:
            raise RuntimeError(f"Failed to add optional {package_name} to group {group} after cache refresh")


def add_package(package_name):
    """Add the latest version of a package using uv."""
    version = get_latest_version(package_name)
    if version:
        print(f"Adding {package_name}>={version}...")
        success = run_uv_add([f"{package_name}>={version}"])
        if not success:
            raise RuntimeError(f"Failed to add {package_name} after cache refresh")
        update_optional_dependencies(package_name, version)
    else:
        print(f"Skipping {package_name} (no version found)")
        
        
def add_package_dev(package_name):
    """Add the latest version of a dev package using uv."""
    version = get_latest_version(package_name)
    if version:
        print(f"Adding {package_name}>={version} as dev dependency...")
        success = run_uv_add(["--dev", f"{package_name}>={version}"])
        if not success:
            raise RuntimeError(f"Failed to add dev {package_name} after cache refresh")
        update_optional_dependencies(package_name, version)
    else:
        print(f"Skipping {package_name} (no version found)")


def main():
    
    dev_packages = ["mikro-next", "alpaka", "kraph", "fluss-next", "reaktion-next", "lovekit", "unlok-next", "elektro"]
    packages = ["rekuest-next", "kabinet", "turms", "fakts-next", "rath", "koil", "dokker"]
    
    
    
    for package in packages:
        add_package(package)
        
    for dev_package in dev_packages:
        add_package_dev(dev_package)

if __name__ == "__main__":
    
    
    
    
    
    main()
