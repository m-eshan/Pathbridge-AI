"""
Data Loader Module for Career Guidance System
Loads and validates all psychometric instruments, ESCO taxonomy, O*NET data, and JobHop transition datasets.
"""

import os
import logging
from typing import Dict, Tuple, Optional
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "datasets")


class DataLoader:
    """Utility class to load and validate all required datasets for the career guidance pipeline."""

    def __init__(self, data_dir: str = DEFAULT_DATA_DIR):
        self.data_dir = data_dir
        self.onet_dir = os.path.join(self.data_dir, "db_31_0_excel")

    def load_bigfive_items(self, filename: str = "ipip_bigfive_20item.csv") -> pd.DataFrame:
        """Load and validate the Mini-IPIP Big Five instrument."""
        filepath = os.path.join(self.data_dir, filename)
        if not os.path.exists(filepath):
            # Fallback to 50-item if 20-item missing
            fallback = os.path.join(self.data_dir, "ipip_bigfive_50item.csv")
            if os.path.exists(fallback):
                filepath = fallback

        df = pd.read_csv(filepath)

        # Sanity checks
        expected_cols = ["item_id", "trait", "keying", "item_text", "scoring_note"]
        for col in expected_cols:
            assert col in df.columns, f"Missing column {col} in {filename}"
            assert df[col].isnull().sum() == 0, f"Null values found in key column {col} of {filename}"

        assert len(df) in [20, 50], f"Expected 20 or 50 Big Five items, found {len(df)}"
        expected_traits = {"Extraversion", "Agreeableness", "Conscientiousness", "Emotional Stability", "Intellect/Imagination"}
        actual_traits = set(df["trait"].unique())
        assert expected_traits == actual_traits, f"Unexpected traits: {actual_traits}"

        logger.info(f"Loaded Big Five instrument: {len(df)} items across {len(actual_traits)} traits.")
        return df

    def load_riasec_items(self, filename: str = "onet_riasec_30item.csv") -> pd.DataFrame:
        """Load and validate the O*NET RIASEC instrument."""
        filepath = os.path.join(self.data_dir, filename)
        if not os.path.exists(filepath):
            fallback = os.path.join(self.data_dir, "onet_riasec_60item.csv")
            if os.path.exists(fallback):
                filepath = fallback

        df = pd.read_csv(filepath)

        # Sanity checks
        expected_cols = ["item_id", "trait", "item_text"]
        for col in expected_cols:
            assert col in df.columns, f"Missing column {col} in {filename}"
            assert df[col].isnull().sum() == 0, f"Null values found in key column {col} of {filename}"

        assert len(df) in [30, 60], f"Expected 30 or 60 RIASEC items, found {len(df)}"
        expected_traits = {"Realistic", "Investigative", "Artistic", "Social", "Enterprising", "Conventional"}
        actual_traits = set(df["trait"].unique())
        assert expected_traits == actual_traits, f"Unexpected RIASEC traits: {actual_traits}"

        logger.info(f"Loaded RIASEC instrument: {len(df)} items across {len(actual_traits)} categories.")
        return df

    def load_esco_data(self) -> Dict[str, pd.DataFrame]:
        """Load ESCO occupations, skills, and occupation-skill relations."""
        occ_file = os.path.join(self.data_dir, "occupations_en.csv")
        skills_file = os.path.join(self.data_dir, "skills_en.csv")
        rel_file = os.path.join(self.data_dir, "occupationSkillRelations_en.csv")

        for f in [occ_file, skills_file, rel_file]:
            if not os.path.exists(f):
                raise FileNotFoundError(f"Required ESCO file missing: {f}")

        logger.info("Loading ESCO classification CSVs...")
        occ_df = pd.read_csv(occ_file)
        skills_df = pd.read_csv(skills_file)
        rel_df = pd.read_csv(rel_file)

        # Sanity checks
        assert occ_df["conceptUri"].isnull().sum() == 0, "Null conceptUri found in ESCO occupations"
        assert skills_df["conceptUri"].isnull().sum() == 0, "Null conceptUri found in ESCO skills"
        assert rel_df["occupationUri"].isnull().sum() == 0, "Null occupationUri in ESCO relations"
        assert rel_df["skillUri"].isnull().sum() == 0, "Null skillUri in ESCO relations"

        logger.info(f"Loaded ESCO: {len(occ_df)} occupations, {len(skills_df)} skills, {len(rel_df)} occupation-skill relations.")
        return {
            "occupations": occ_df,
            "skills": skills_df,
            "relations": rel_df
        }

    def load_onet_data(self) -> Dict[str, pd.DataFrame]:
        """Load O*NET occupations, essential skills, and knowledge tables."""
        occ_file = os.path.join(self.onet_dir, "Occupation Data.xlsx")
        skills_file = os.path.join(self.onet_dir, "Essential Skills.xlsx")
        know_file = os.path.join(self.onet_dir, "Knowledge.xlsx")

        for f in [occ_file, skills_file, know_file]:
            if not os.path.exists(f):
                raise FileNotFoundError(f"Required O*NET file missing: {f}")

        logger.info("Loading O*NET database Excel files...")
        occ_df = pd.read_excel(occ_file)
        skills_df = pd.read_excel(skills_file)
        know_df = pd.read_excel(know_file)

        # Sanity checks
        assert occ_df["O*NET-SOC Code"].isnull().sum() == 0, "Null O*NET code in occupation data"
        assert skills_df["O*NET-SOC Code"].isnull().sum() == 0, "Null O*NET code in skills data"
        assert know_df["O*NET-SOC Code"].isnull().sum() == 0, "Null O*NET code in knowledge data"

        logger.info(f"Loaded O*NET: {len(occ_df)} occupations, {len(skills_df)} skills records, {len(know_df)} knowledge records.")
        return {
            "occupations": occ_df,
            "skills": skills_df,
            "knowledge": know_df
        }

    def load_jobhop_data(self) -> Dict[str, pd.DataFrame]:
        """Load JobHop v2 transition dataset parquet files."""
        train_file = os.path.join(self.data_dir, "JobHop_v2_train.parquet")
        val_file = os.path.join(self.data_dir, "JobHop_v2_val.parquet")
        test_file = os.path.join(self.data_dir, "JobHop_v2_test.parquet")

        for f in [train_file, val_file, test_file]:
            if not os.path.exists(f):
                raise FileNotFoundError(f"JobHop dataset missing: {f}")

        logger.info("Loading JobHop v2 parquet files...")
        train_df = pd.read_parquet(train_file)
        val_df = pd.read_parquet(val_file)
        test_df = pd.read_parquet(test_file)

        # Sanity checks
        assert train_df["resume_id"].isnull().sum() == 0, "Null resume_id in JobHop train"
        assert train_df["matched_code"].isnull().sum() == 0, "Null matched_code in JobHop train"

        logger.info(f"Loaded JobHop v2: train={len(train_df)}, val={len(val_df)}, test={len(test_df)} transition records.")
        return {
            "train": train_df,
            "val": val_df,
            "test": test_df
        }

    def load_all(self) -> Dict[str, object]:
        """Load and return all datasets in a single dictionary."""
        logger.info("Starting complete dataset load and sanity check...")
        bigfive = self.load_bigfive_items()
        riasec = self.load_riasec_items()
        esco = self.load_esco_data()
        onet = self.load_onet_data()
        jobhop = self.load_jobhop_data()

        logger.info("ALL DATASETS LOADED AND SANITY CHECKS PASSED PERFECTLY!")
        return {
            "bigfive": bigfive,
            "riasec": riasec,
            "esco": esco,
            "onet": onet,
            "jobhop": jobhop
        }


if __name__ == "__main__":
    loader = DataLoader()
    data = loader.load_all()
    print("\n--- DATA LOADING SANITY CHECK SUMMARY ---")
    print(f"Big Five Items: {len(data['bigfive'])}")
    print(f"RIASEC Items:   {len(data['riasec'])}")
    print(f"ESCO Occupations: {len(data['esco']['occupations'])}")
    print(f"ESCO Skills:      {len(data['esco']['skills'])}")
    print(f"ESCO Relations:   {len(data['esco']['relations'])}")
    print(f"O*NET Occupations: {len(data['onet']['occupations'])}")
    print(f"JobHop Train Rows: {len(data['jobhop']['train'])}")
