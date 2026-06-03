import argparse
import sys
import requests
import os
import time
import tempfile
import json
import hashlib
from requests_toolbelt.multipart.encoder import MultipartEncoder, MultipartEncoderMonitor
from tqdm import tqdm
from colorama import init, Fore, Style

# Initialize colored output
init()

# Cache configuration
CACHE_MAX_AGE = 3600  # 60 minutes


def get_cache_file(proxy_key=None):
    """Get appropriate cache file path based on proxy."""
    temp_dir = tempfile.gettempdir()
    if proxy_key:
        key_hash = hashlib.md5(proxy_key.encode()).hexdigest()[:8]
        return os.path.join(temp_dir, f'gofile_server_{key_hash}.json')
    return os.path.join(temp_dir, 'gofile_server_default.json')


def get_cached_server(proxy_key=None):
    """Return cached server name if valid (< 60min), else None."""
    cache_file = get_cache_file(proxy_key)
    try:
        if os.path.exists(cache_file):
            with open(cache_file, 'r') as f:
                data = json.load(f)
                if time.time() - data.get('timestamp', 0) < CACHE_MAX_AGE:
                    return data.get('server')
    except Exception:
        pass
    return None


def save_server(server_name, proxy_key=None):
    """Save server name to cache with current timestamp."""
    cache_file = get_cache_file(proxy_key)
    try:
        with open(cache_file, 'w') as f:
            json.dump({
                'server': server_name,
                'timestamp': time.time()
            }, f)
    except Exception:
        pass


def invalidate_cache(proxy_key=None):
    """Remove cache file."""
    try:
        cache_file = get_cache_file(proxy_key)
        if os.path.exists(cache_file):
            os.remove(cache_file)
    except Exception:
        pass


def get_upload_server(proxies=None):
    """Fetch available upload server from GoFile API."""
    proxy_key = proxies.get('http') if proxies else None
    
    cached = get_cached_server(proxy_key)
    if cached:
        return cached
    
    try:
        response = requests.get(
            'https://api.gofile.io/servers', 
            timeout=30, 
            proxies=proxies
        )
        if response.status_code != 200:
            print(f"{Fore.RED}[!] error: failed to get server list (status {response.status_code}){Style.RESET_ALL}")
            return None
            
        data = response.json()
        if data.get('status') != 'ok':
            print(f"{Fore.RED}[!] error: invalid server response{Style.RESET_ALL}")
            return None
            
        servers = data.get('data', {}).get('servers', [])
        if not servers:
            print(f"{Fore.RED}[!] error: no servers available{Style.RESET_ALL}")
            return None
        
        server_name = servers[0].get('name') if isinstance(servers[0], dict) else servers[0]
        if not server_name:
            print(f"{Fore.RED}[!] error: invalid server data{Style.RESET_ALL}")
            return None
            
        save_server(server_name, proxy_key)
        return server_name
        
    except Exception as e:
        print(f"{Fore.RED}[!] error getting server: {str(e)}{Style.RESET_ALL}")
        return None


def upload_file(file_path, file_index=None, total_files=None, proxies=None, log_path=None):
    """Upload a single file to Gofile with progress tracking."""
    if not os.path.isfile(file_path):
        print(f"{Fore.RED}[!] error: '{file_path}' missing file{Style.RESET_ALL}")
        return None
    
    file_handle = None
    proxy_key = proxies.get('http') if proxies else None
    
    try:
        file_size = os.path.getsize(file_path)
        if file_size == 0:
            print(f"{Fore.RED}[!] error: empty file{Style.RESET_ALL}")
            return None
        
        if file_index is not None and total_files is not None:
            print(f"{Fore.BLUE}[>] [{file_index}/{total_files}] {os.path.basename(file_path)}{Style.RESET_ALL}")
        
        server = get_upload_server(proxies)
        if not server:
            return None
            
        upload_url = f"https://{server}.gofile.io/uploadfile"
        
        filename = os.path.basename(file_path)
        file_handle = open(file_path, 'rb')
        
        encoder = MultipartEncoder(
            fields={'file': (filename, file_handle, 'application/octet-stream')}
        )
        
        pbar = tqdm(
            total=file_size, 
            unit='B', 
            unit_scale=True, 
            desc=f"{Fore.YELLOW}[>] uploading{Style.RESET_ALL}", 
            leave=True
        )
        
        def update_progress(monitor):
            pbar.update(monitor.bytes_read - pbar.n)
        
        progress_encoder = MultipartEncoderMonitor(encoder, update_progress)
        start_time = time.time()
        
        response = requests.post(
            upload_url,
            data=progress_encoder,
            headers={'Content-Type': encoder.content_type},
            timeout=300,
            proxies=proxies
        )
        
        pbar.close()
        elapsed_time = time.time() - start_time
        
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'ok':
                download_link = data['data']['downloadPage']
                print(f"{Fore.GREEN}[+] link: {download_link} ({elapsed_time:.1f}s){Style.RESET_ALL}")
                
                if log_path:
                    try:
                        with open(log_path, 'a', encoding='utf-8') as log_file:
                            log_file.write(f"{download_link}\n")
                    except Exception as e:
                        print(f"{Fore.RED}[!] error saving link: {str(e)}{Style.RESET_ALL}")
                
                return {'link': download_link, 'filename': filename}
            else:
                print(f"{Fore.RED}[!] error: upload rejected: {data.get('message', 'unknown')}{Style.RESET_ALL}")
                invalidate_cache(proxy_key)
                return None
        else:
            print(f"{Fore.RED}[!] error HTTP {response.status_code}: {response.text[:200]}{Style.RESET_ALL}")
            invalidate_cache(proxy_key)
            return None
                
    except Exception as e:
        print(f"{Fore.RED}[!] error: {str(e)}{Style.RESET_ALL}")
        invalidate_cache(proxy_key)
        return None
        
    finally:
        if file_handle:
            file_handle.close()


def upload_with_retries(path, file_index=None, total_files=None, proxies=None, log_path=None):
    """Retry mechanism (3 attempts total)."""
    max_attempts = 3
    proxy_key = proxies.get('http') if proxies else None
    
    for attempt in range(1, max_attempts + 1):
        result = upload_file(path, file_index, total_files, proxies=proxies, log_path=log_path)
        if result is not None:
            return result
        
        if attempt < max_attempts:
            invalidate_cache(proxy_key)
            print(f"{Fore.RED}[!] retry in 10s.. [{attempt}/{max_attempts - 1}]{Style.RESET_ALL}")
            time.sleep(10)

    return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="upload files or folders to Gofile")
    parser.add_argument("path", help="path to the file or folder to upload")
    parser.add_argument("--log", action="store_true", help="save upload links to _links.txt file")

    parser.add_argument(
        "--wait",
        type=int,
        default=5,
        help="seconds to wait between uploads (default: 5sec)"
    )
    
    parser.add_argument(
        "--proxy",
        nargs='?',
        const='socks5://127.0.0.1:9050',
        default=None,
        help="use proxy (default if empty: socks5://127.0.0.1:9050, or specify custom proxy URL)"
    )

    args = parser.parse_args()
    
    proxies = None
    if args.proxy is not None:
        proxies = {'http': args.proxy, 'https': args.proxy}
        print(f"{Fore.CYAN}[>] using proxy: {args.proxy}{Style.RESET_ALL}")
    
    upload_results = []
    total_files = 0
    
    # Single file mode
    if os.path.isfile(args.path):
        total_files = 1
        
        single_log_path = None
        if args.log:
            output_dir = os.path.dirname(args.path)
            filename = os.path.basename(args.path)
            single_log_path = os.path.join(
                output_dir if output_dir else '.', 
                f"{os.path.splitext(filename)[0]}_links.txt"
            )
        
        result = upload_with_retries(args.path, proxies=proxies, log_path=single_log_path)
        if result:
            upload_results.append(result)

    # Folder mode
    elif os.path.isdir(args.path):
        files = sorted([
            os.path.join(args.path, f)
            for f in os.listdir(args.path)
            if os.path.isfile(os.path.join(args.path, f))
        ], key=lambda x: os.path.basename(x).lower())
        total_files = len(files)
        
        for index, file_path in enumerate(files, 1):
            result = upload_with_retries(file_path, index, total_files, proxies=proxies, log_path=None)
            if result:
                upload_results.append(result)

            if index < total_files:
                print(f"{Fore.YELLOW}[>] waiting {args.wait}s..{Style.RESET_ALL}")
                time.sleep(args.wait)
        
        # Create single log file for folder with format: link - filename
        if args.log and upload_results:
            # Get actual folder name from path (handles ./folder, /path/to/folder, .)
            folder_path = os.path.normpath(args.path)
            folder_name = os.path.basename(folder_path)
            
            # Handle case where path is '.' or ends with separator
            if not folder_name or folder_name == '.':
                folder_name = os.path.basename(os.getcwd())
            
            parent_dir = os.path.dirname(folder_path) if os.path.dirname(folder_path) else '.'
            
            folder_log_path = os.path.join(parent_dir, f"{folder_name}_links.txt")
            
            try:
                with open(folder_log_path, 'w', encoding='utf-8') as log_file:
                    for result in upload_results:
                        log_file.write(f"{result['link']} - {result['filename']}\n")
            except Exception as e:
                print(f"{Fore.RED}[!] error saving links file: {str(e)}{Style.RESET_ALL}")

    else:
        print(f"{Fore.RED}[!] error: '{args.path}' invalid path{Style.RESET_ALL}")
        sys.exit(1)
    
    if upload_results:
        print(f"\n{Fore.YELLOW}[>] uploads finished ({len(upload_results)}/{total_files}){Style.RESET_ALL}")
        for result in upload_results:
            print(f"{Fore.GREEN}[+] {result['link']}{Style.RESET_ALL} - {Fore.BLUE}{result['filename']}{Style.RESET_ALL}")
