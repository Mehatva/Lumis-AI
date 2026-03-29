import os
import glob
import imageio

webp_files = glob.glob('*.webp')
files_to_convert = webp_files

for file in files_to_convert:
    base_name = os.path.splitext(file)[0]
    output_file = f"{base_name}.mp4"
    if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
        continue
    print(f"Converting {file} to {output_file}...")
    try:
        reader = imageio.get_reader(file)
        
        # safely get fps or default to 15
        meta = reader.get_meta_data()
        fps = meta.get('fps', 15)
        if hasattr(meta, 'duration') and meta['duration']:
            try:
                fps = 1000 / meta['duration']
            except:
                pass
                
        writer = imageio.get_writer(output_file, fps=fps, macro_block_size=2)
        for frame in reader:
            writer.append_data(frame)
        writer.close()
    except Exception as e:
        print(f"Error converting {file}: {e}")

print("Conversion complete.")
