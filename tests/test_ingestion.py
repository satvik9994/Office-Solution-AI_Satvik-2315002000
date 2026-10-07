import unittest
import sys, os
sys.path.insert(0, os.path.abspath('src'))

from ingestion.file_reader import (
    load_calculations,
    load_dependencies,
    load_tableau_xml,
    load_incorrect_dax,
    load_ground_truth,
    load_visuals,
    load_sample_data,
)


class TestIngestion(unittest.TestCase):

    def test_load_tableau_calculations(self):
        calcs = load_calculations("data/tableau_calculations.json")
        self.assertEqual(len(calcs), 4)
        calc_map = {c.id: c for c in calcs}
        self.assertIn("calc_1", calc_map)
        self.assertEqual(calc_map["calc_1"].name, "Profit_Ratio")
        self.assertEqual(calc_map["calc_1"].formula, "SUM([Profit]) / SUM([Sales])")

    def test_load_dependencies_synthesized_id(self):
        deps = load_dependencies("data/tableau_dependencies.json")
        self.assertEqual(len(deps), 3)
        self.assertEqual(deps[0].name, "Step1")
        self.assertEqual(deps[0].id, "dep_Step1")
        self.assertEqual(deps[1].formula, "[Step1] / SUM([Sales])")

    def test_load_tableau_xml(self):
        xml_calcs = load_tableau_xml("data/tableau_xml.xml")
        self.assertEqual(len(xml_calcs), 2)
        names = {c.name: c.formula for c in xml_calcs}
        self.assertIn("RunningSales", names)
        self.assertEqual(names["RunningSales"], "RUNNING_SUM(SUM([Sales]))")

    def test_load_incorrect_and_ground_truth_dax(self):
        inc = load_incorrect_dax("data/incorrect_dax.json")
        gt = load_ground_truth("data/ground_truth.json")
        self.assertEqual(len(inc), 4)
        self.assertEqual(len(gt), 4)
        self.assertEqual(inc["calc_1"].dax, "SUM(Sales) / SUM(Profit)")
        self.assertEqual(gt["calc_1"].dax, "DIVIDE(SUM(Profit), SUM(Sales))")
        self.assertIn("...", gt["calc_3"].dax)

    def test_load_visuals(self):
        vis = load_visuals("data/visuals.json")
        self.assertEqual(len(vis), 2)
        self.assertEqual(vis[0].expected_powerbi, "clustered column chart")
        self.assertEqual(vis[1].expected_powerbi, "line chart")

    def test_load_sample_data_csv_and_xlsx(self):
        df_csv = load_sample_data("data/sample_data.csv")
        self.assertEqual(df_csv.shape, (5, 5))
        self.assertEqual(list(df_csv.columns), ["Region", "Sales", "Profit", "Cost", "Date"])
        self.assertEqual(df_csv["Sales"].sum(), 46000)

        df_xlsx = load_sample_data("data/sample_data.xlsx")
        self.assertEqual(df_xlsx.shape, (5, 5))
        self.assertEqual(list(df_xlsx.columns), ["Region", "Sales", "Profit", "Cost", "Date"])
        self.assertEqual(df_xlsx["Sales"].sum(), 46000)


if __name__ == "__main__":
    unittest.main()
