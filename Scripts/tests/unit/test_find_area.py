#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import numpy
import pandas
import unittest


class AreaFindTest(unittest.TestCase):
    def test_find_area(self):
        mapping = pandas.Series({
            101: "Uusimaa",
            2021: "Uusimaa",
            5500: "Uusimaa",
            13561: "Varsinais-Suomi",
        })
        agg = mapping.drop_duplicates()
        a = pandas.DataFrame(0, agg, agg)
        county1 = mapping.iat[0]
        county2 = mapping.iat[3]
        a.at[county1, county2] += 1
        self.assertEquals(a.at["Uusimaa", "Varsinais-Suomi"], 1)
