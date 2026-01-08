import argparse, sys, requests, os, time, _io
from requests_toolbelt.multipart.encoder import MultipartEncoder, MultipartEncoderMonitor
from tqdm import tqdm
from colorama import init, Fore, Style

# Initialize colored output
init()

def upload_file(file_path, file_index=None, total_files=None):
    # Check existence
    if not os.path.isfile(file_path):
        print(f"{Fore.RED}[!] error: '{file_path}' missing file{Style.RESET_ALL}")
        return None
    
    try:
        file_size = os.path.getsize(file_path)
        if file_size == 0:
            print(f"{Fore.RED}[!] error: empty file{Style.RESET_ALL}")
            return None
        
        # File index display for folder mode
        if file_index is not None and total_files is not None:
            print(f"{Fore.BLUE}[>] [{file_index}/{total_files}] {os.path.basename(file_path)}{Style.RESET_ALL}")
        
        # Prepare streamed upload
        encoder = MultipartEncoder(
            fields={'file': (os.path.basename(file_path), open(file_path, 'rb'), 'application/octet-stream')}
        )
        
        # Progress bar
        pbar = tqdm(total=file_size, unit='B', unit_scale=True, desc=f"{Fore.YELLOW}[>] uploading{Style.RESET_ALL}", ascii=True, leave=True)
        
        def update_progress(monitor):
            pbar.update(monitor.bytes_read - pbar.n)
        
        progress_encoder = MultipartEncoderMonitor(encoder, update_progress)
        start_time = time.time()
        
        # Upload request
        response = requests.post(
            'https://upload.gofile.io/uploadfile',
            data=progress_encoder,
            headers={'Content-Type': encoder.content_type}
        )
        
        pbar.close()
        elapsed_time = time.time() - start_time
        
        # Interpret response
        if response.status_code == 200:
            data = response.json()
            if data['status'] == 'ok':
                download_link = data['data']['downloadPage']
                print(f"{Fore.GREEN}[+] link: {download_link}{Style.RESET_ALL}")
                
                # Optional link logging
                if args.log:
                    output_dir = os.path.dirname(file_path) if os.path.isfile(file_path) else file_path
                    filename = os.path.basename(file_path)
                    log_file_path = os.path.join(output_dir, f"{os.path.splitext(filename)[0]}_links.txt")
                    try:
                        with open(log_file_path, 'w', encoding='utf-8') as log_file:
                            log_file.write(f"{download_link}\n")
                    except Exception as e:
                        print(f"{Fore.RED}[!] error saving link to file: {str(e)}{Style.RESET_ALL}")
                
                return {'link': download_link, 'filename': os.path.basename(file_path)}
            else:
                print(f"{Fore.RED}[!] error upload failed: {data.get('message', 'Unknown error')}")
                return None
        else:
            print(f"{Fore.RED}[!] error upload failed {response.status_code}: {response.text}")
            return None
                
    except Exception as e:
        print(f"{Fore.RED}[!] error {str(e)}{Style.RESET_ALL}")
        return None

    finally:
        # Close file stream if created
        if 'encoder' in locals():
            for field in encoder.fields.values():
                if isinstance(field[1], _io.BufferedReader):
                    field[1].close()


def upload_with_retries(path, file_index=None, total_files=None):
    # Retry mechanism (3 attempts total)
    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        result = upload_file(path, file_index, total_files)
        if result is not None:
            return result
        
        # Retry delay
        if attempt < max_attempts:
            print(f"{Fore.RED}[!] error upload failed, retrying in 5min.. [{attempt}/{max_attempts - 1}]{Style.RESET_ALL}")
            time.sleep(5 * 60)

    return None


if __name__ == "__main__":
    # CLI arguments
    parser = argparse.ArgumentParser(description="Upload files or folders to Gofile")
    parser.add_argument("path", help="Path to the file or folder to upload")
    parser.add_argument("--log", action="store_true", help="Save upload links to individual <filename>_links.txt files")

    # Delay between multi-file uploads
    parser.add_argument(
        "--wait",
        type=int,
        default=1,
        help="Minutes to wait between uploads when uploading multiple files (default: 1 minute)"
    )

    args = parser.parse_args()
    
    upload_results = []
    
    # Single file
    if os.path.isfile(args.path):
        result = upload_with_retries(args.path)
        if result:
            upload_results.append(result)

    # Folder upload
    elif os.path.isdir(args.path):
        files = [
            os.path.join(args.path, f)
            for f in os.listdir(args.path)
            if os.path.isfile(os.path.join(args.path, f))
        ]
        total_files = len(files)
        
        for index, file_path in enumerate(files, 1):
            result = upload_with_retries(file_path, index, total_files)
            if result:
                upload_results.append(result)

            # Wait between uploads
            if index < total_files:
                print(f"{Fore.CYAN}[>] waiting {args.wait}min..{Style.RESET_ALL}")
                time.sleep(args.wait * 60)

    else:
        print(f"{Fore.RED}[!] error '{args.path}' invalid path{Style.RESET_ALL}")
        sys.exit(1)
    
    # Summary output
    if upload_results:
        print(f"{Fore.YELLOW} -- [results] -- {Style.RESET_ALL}")
        for result in upload_results:
            print(f"[+] {Fore.GREEN}{result['link']}{Style.RESET_ALL} {Fore.BLUE}{result['filename']}{Style.RESET_ALL}")
