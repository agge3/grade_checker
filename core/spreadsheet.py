import pandas as pd

inpath = "input.xlsx"
outpath = "output.xlsx"

new_entries = [
    {"id": "xxx", "name": "New Name", "compiles": "Yes", "testcases": "5"},
    {"id": "yyy", "name": "Another Name", "compiles": "No", "testcases": "3"}
]

def main(path):
    writer = pd.ExcelWriter('file.xlsx', engine='openpyxl')
    df = pd.DataFrame()
    df.to_excel(writer, sheet_name='empty')


    df.columns = df.columns.str.strip()

    for entry in new_data:
        mask = df['id'] == entry['id']
        df.loc[mask, entry.keys()] = pd.DataFrame([entry])

    df.to_excel(output_path, index=False)



    writer.close()


if __name__ == "__main__": 
    main()
