#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import numpy
import pandas
import unittest


class AreaFindTest(unittest.TestCase):
    def test_find_area(self):
        mapping = pandas.Series({
            202: "Uusimaa",
            2037: "Uusimaa",
            4101: "Uusimaa",
            12614: "Varsinais-Suomi",
        })
        agg = mapping.drop_duplicates()
        a = pandas.DataFrame(0, agg, agg)
        county1 = mapping.iat[0]
        county2 = mapping.iat[3]
        a.at[county1, county2] += 1
        self.assertEquals(a.at["Uusimaa", "Varsinais-Suomi"], 1)
