import argparse, sys, requests, os, time, _io
from requests_toolbelt.multipart.encoder import MultipartEncoder, MultipartEncoderMonitor
from tqdm import tqdm
from colorama import init, Fore, Style

# Initialize colorama for cross-platform colored output
init()

def upload_file(file_path, file_index=None, total_files=None):
    # Check if file exists
    if not os.path.isfile(file_path):
        print(f"{Fore.RED}Error: File '{file_path}' does not exist{Style.RESET_ALL}")
        return None
    
    try:
        # Get file size
        file_size = os.path.getsize(file_path)
        if file_size == 0:
            print(f"{Fore.RED}Error: File is empty{Style.RESET_ALL}")
            return None
        
        # Print file name with index if processing a folder
        if file_index is not None and total_files is not None:
            print(f"{Fore.BLUE}-> [{file_index}/{total_files}] {os.path.basename(file_path)}{Style.RESET_ALL}")
        
        # Create a MultipartEncoder for streaming upload
        encoder = MultipartEncoder(
            fields={'file': (os.path.basename(file_path), open(file_path, 'rb'), 'application/octet-stream')}
        )
        
        # Create a progress bar with yellow color
        pbar = tqdm(total=file_size, unit='B', unit_scale=True, desc=f"{Fore.YELLOW}Uploading{Style.RESET_ALL}", ascii=True, leave=True)
        
        def update_progress(monitor):
            # Update progress bar with the difference in bytes read
            pbar.update(monitor.bytes_read - pbar.n)
        
        # Use MultipartEncoderMonitor for progress tracking
        progress_encoder = MultipartEncoderMonitor(encoder, update_progress)
        
        # Record start time for speed calculation
        start_time = time.time()
        
        # Make POST request to Gofile API with streaming
        response = requests.post(
            'https://upload.gofile.io/uploadfile',
            data=progress_encoder,
            headers={'Content-Type': encoder.content_type}
        )
        
        # Close the progress bar
        pbar.close()
        
        # Calculate upload speed
        elapsed_time = time.time() - start_time
        upload_speed = file_size / elapsed_time / 1024 / 1024 if elapsed_time > 0 else 0
        
        # Check response status
        if response.status_code == 200:
            data = response.json()
            if data['status'] == 'ok':
                download_link = data['data']['downloadPage']
                # Print download link in green
                print(f"{Fore.GREEN}{download_link}{Style.RESET_ALL}\n")
                
                # Save the link to a file named <filename>_links.txt
                if args.log:
                    output_dir = os.path.dirname(file_path) if os.path.isfile(file_path) else file_path
                    filename = os.path.basename(file_path)
                    log_file_path = os.path.join(output_dir, f"{os.path.splitext(filename)[0]}_links.txt")
                    try:
                        with open(log_file_path, 'w', encoding='utf-8') as log_file:
                            log_file.write(f"{download_link}\n")
                    except Exception as e:
                        print(f"{Fore.RED}Error saving link to file: {str(e)}{Style.RESET_ALL}")
                
                return {'link': download_link, 'filename': os.path.basename(file_path)}
            else:
                print(f"Upload failed: {data.get('message', 'Unknown error')}")
                return None
        else:
            print(f"Upload failed with status code: {response.status_code}")
            print(f"Response: {response.text}")
            return None
                
    except Exception as e:
        print(f"{Fore.RED}Error during upload: {str(e)}{Style.RESET_ALL}")
        return None
    finally:
        # Ensure the file is closed if it was opened
        if 'encoder' in locals():
            for field in encoder.fields.values():
                if isinstance(field[1], _io.BufferedReader):
                    field[1].close()

if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Upload files or folders to Gofile")
    parser.add_argument("path", help="Path to the file or folder to upload")
    parser.add_argument("--log", action="store_true", help="Save upload links to individual <filename>_links.txt files")
    
    # Parse arguments
    args = parser.parse_args()
    
    upload_results = []
    
    if os.path.isfile(args.path):
        # Single file upload
        result = upload_file(args.path)
        if result:
            upload_results.append(result)
    elif os.path.isdir(args.path):
        # Folder upload
        files = [os.path.join(args.path, f) for f in os.listdir(args.path) if os.path.isfile(os.path.join(args.path, f))]
        total_files = len(files)
        
        for index, file_path in enumerate(files, 1):
            result = upload_file(file_path, index, total_files)
            if result:
                upload_results.append(result)
    else:
        print(f"{Fore.RED}Error: '{args.path}' is neither a file nor a directory{Style.RESET_ALL}")
        sys.exit(1)
    
    # Print summary of uploaded files and their links
    if upload_results:
        print(f"{Fore.YELLOW}--- Uploaded files ---{Style.RESET_ALL}")
        for result in upload_results:
            print(f"{Fore.GREEN}{result['link']}{Style.RESET_ALL} {Fore.BLUE}{result['filename']}{Style.RESET_ALL}")