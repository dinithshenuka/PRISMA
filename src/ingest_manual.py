import pandas as pd
import os
import glob

def load_manual_files(data_dir="data/raw"):
    """
    Loads all CSV files in the data/raw directory.
    Assumes standard columns: Title, Abstract, DOI, Year
    """
    print(f"Checking for manual exports in {data_dir}...")
    
    csv_files = glob.glob(os.path.join(data_dir, "*.csv"))
    
    if not csv_files:
        print("No manual CSV files found.")
        return pd.DataFrame()
        
    dfs = []
    for file in csv_files:
        try:
            print(f"Loading {file}...")
            df = pd.read_csv(file)
            
            # Map standard columns to lower case to match API format
            # This mapping might need adjustment based on Scopus/Embase actual CSV headers
            column_mapping = {
                'Title': 'title',
                'Abstract': 'abstract',
                'DOI': 'doi',
                'Year': 'year'
            }
            
            # Rename columns if they exist
            df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})
            
            # Keep only required columns if they exist
            required_cols = ['title', 'abstract', 'doi', 'year']
            available_cols = [col for col in required_cols if col in df.columns]
            
            df = df[available_cols].copy()
            df['source'] = f"Manual_{os.path.basename(file)}"
            
            # Filter out rows missing title or abstract
            if 'title' in df.columns and 'abstract' in df.columns:
                df = df.dropna(subset=['title', 'abstract'])
                dfs.append(df)
            else:
                print(f"Skipping {file} due to missing 'Title' or 'Abstract' columns.")
                
        except Exception as e:
            print(f"Error reading {file}: {e}")
            
    if dfs:
        return pd.concat(dfs, ignore_index=True)
    return pd.DataFrame()
