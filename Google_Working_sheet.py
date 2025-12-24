import pandas as pd
def write_to_v1(old_df, new_df):
            # Merge the DataFrames on 'lead_id' with an outer join to get all records

            merged_df = pd.merge(old_df, new_df, on='lead_id', how='outer', suffixes=('_old', '_new'))

            # Update matching records: If a value is present in the new dataframe, update the old dataframe value
            for col in new_df.columns:
                    if col + '_new' in merged_df.columns and col + '_old' in merged_df.columns:
                    # Update the old column with the new value where it exists
                        merged_df[col + '_old'] = merged_df.apply(lambda x: x[col + '_new'] if pd.notnull(x[col + '_new']) else x[col + '_old'], axis=1)

            # Extract the original column names from the old dataframe
            original_columns = old_df.columns
            # Create a new dataframe with these columns, taking values from the merged_df
            final_df = merged_df[[col + '_old' if col + '_old' in merged_df.columns else col for col in original_columns]].copy()
            # Rename columns back to original
            final_df.columns = original_columns
            return final_df
