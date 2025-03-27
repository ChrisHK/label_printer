import csv
import sys
from print_label_html import print_new_record  # 更新导入

def find_record_by_sn(sn, csv_file_path):
    try:
        with open(csv_file_path, 'r', encoding='utf-8') as file:
            csv_reader = csv.DictReader(file)
            for row in csv_reader:
                if row.get('SN', '').strip() == sn.strip():
                    return row
    except FileNotFoundError:
        print(f"Error: CSV file not found at {csv_file_path}")
        return None
    except Exception as e:
        print(f"Error reading CSV: {str(e)}")
        return None
    return None

def main():
    csv_file_path = 'your_data.csv'  # Replace with your CSV file path
    
    while True:
        sn = input("Please scan or enter SN (enter 'q' to quit): ").strip()
        
        if sn.lower() == 'q':
            print("Program terminated")
            break
            
        record = find_record_by_sn(sn, csv_file_path)
        
        if record:
            try:
                print_new_record(record)  # Call the print label function
                print(f"Successfully printed label for SN: {sn}")
            except Exception as e:
                print(f"Error printing label: {str(e)}")
        else:
            print(f"No record found for SN: {sn}")

if __name__ == "__main__":
    main()