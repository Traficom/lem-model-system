# Variables for converting tons to vehicles for each commodity class

vehicle_conversion = {
  "marita": {
    "truck_share": 0.059,
    "trailer_truck_share": 0.941,
		"truck_avg_load": 6.35,
		"trailer_truck_avg_load": 33.32,
		"empty_share": 0.5
  },
  "metsat": {
    "truck_share": 0.008,
    "trailer_truck_share": 0.992,
    "truck_avg_load": 5.91,
    "trailer_truck_avg_load": 46.8,
    "empty_share": 1.0
  },
  "kalevi": {
    "truck_share": 0.059,
    "trailer_truck_share": 0.941,
    "truck_avg_load": 6.35,
    "trailer_truck_avg_load": 33.32,
    "empty_share": 0.5
  },
  "krhiil": {
    "truck_share": 0.042,
    "trailer_truck_share": 0.958,
    "truck_avg_load": 10.59,
		"trailer_truck_avg_load": 39.82,
		"empty_share": 0.5
  },
  "rkoljy": {
    "truck_share": 0.042,
    "trailer_truck_share": 0.958,
    "truck_avg_load": 10.59,
		"trailer_truck_avg_load": 39.82,
		"empty_share": 0.5
  },
  "metkai": {
    "truck_share": 0.241,
    "trailer_truck_share": 0.759,
    "truck_avg_load": 12.5,
		"trailer_truck_avg_load": 36.84,
		"empty_share": 1.0
  },
  "turve": {
    "truck_share": 0.042,
    "trailer_truck_share": 0.958,
    "truck_avg_load": 10.59,
		"trailer_truck_avg_load": 39.82,
		"empty_share": 0.5
  },
  "elint": {
    "truck_share": 0.124,
    "trailer_truck_share": 0.876,
    "truck_avg_load": 5.41,
		"trailer_truck_avg_load": 25.47,
		"empty_share": 0.5
  },
  "tekst": {
    "truck_share": 0.437,
    "trailer_truck_share": 0.563,
    "truck_avg_load": 2.33,
		"trailer_truck_avg_load": 11.49,
		"empty_share": 0.5
  },
  "puukor": {
    "truck_share": 0.031,
    "trailer_truck_share": 0.969,
    "truck_avg_load": 5.84,
		"trailer_truck_avg_load": 35.81,
		"empty_share": 0.5
  },
  "papsel": {
    "truck_share": 0.067,
    "trailer_truck_share": 0.933,
    "truck_avg_load": 4.21,
		"trailer_truck_avg_load": 33.5,
		"empty_share": 0.5
  },
  "pappai": {
    "truck_share": 0.067,
    "trailer_truck_share": 0.933,
    "truck_avg_load": 4.21,
		"trailer_truck_avg_load": 33.5,
		"empty_share": 0.5
  },
  "kokbri": {
    "truck_share": 0.042,
    "trailer_truck_share": 0.958,
    "truck_avg_load": 10.59,
		"trailer_truck_avg_load": 39.82,
		"empty_share": 0.5
  },
  "bensa": {
    "truck_share": 0.024,
    "trailer_truck_share": 0.976,
    "truck_avg_load": 9.36,
		"trailer_truck_avg_load": 41.81,
		"empty_share": 0.5
    },
  "diesel": {
    "truck_share": 0.024,
    "trailer_truck_share": 0.976,
    "truck_avg_load": 9.36,
		"trailer_truck_avg_load": 41.81,
		"empty_share": 0.5
  },
  "kpoljy": {
    "truck_share": 0.024,
    "trailer_truck_share": 0.976,
    "truck_avg_load": 9.36,
		"trailer_truck_avg_load": 41.81,
		"empty_share": 0.5
  },
  "kroljy": {
    "truck_share": 0.024,
    "trailer_truck_share": 0.976,
    "truck_avg_load": 9.36,
		"trailer_truck_avg_load": 41.81,
		"empty_share": 0.5
  },
  "mpoljy": {
    "truck_share": 0.024,
    "trailer_truck_share": 0.976,
    "truck_avg_load": 9.36,
		"trailer_truck_avg_load": 41.81,
		"empty_share": 0.5
  },
  "kemlaa": {
    "truck_share": 0.03,
    "trailer_truck_share": 0.97,
    "truck_avg_load": 3.37,
		"trailer_truck_avg_load": 32.84,
		"empty_share": 1.0
  },
  "kummuo": {
    "truck_share": 0.03,
    "trailer_truck_share": 0.97,
    "truck_avg_load": 3.37,
		"trailer_truck_avg_load": 32.84,
		"empty_share": 1.0
  },
  "minkai": {
    "truck_share": 0.241,
    "trailer_truck_share": 0.759,
    "truck_avg_load": 12.5,
		"trailer_truck_avg_load": 36.84,
		"empty_share": 1.0
  },
  "rauter": {
    "truck_share": 0.267,
    "trailer_truck_share": 0.733,
    "truck_avg_load": 4.44,
		"trailer_truck_avg_load": 22.49,
		"empty_share": 1.0
  },
  "jaloml": {
    "truck_share": 0.267,
    "trailer_truck_share": 0.733,
    "truck_avg_load": 4.44,
		"trailer_truck_avg_load": 22.49,
		"empty_share": 1.0
  },
  "mltuot": {
    "truck_share": 0.267,
    "trailer_truck_share": 0.733,
    "truck_avg_load": 12.5,
		"trailer_truck_avg_load": 46.8,
		"empty_share": 1.0
  },
  "elektr": {
    "truck_share": 0.267,
    "trailer_truck_share": 0.733,
    "truck_avg_load": 4.44,
		"trailer_truck_avg_load": 22.49,
		"empty_share": 1.0
  },
  "konela": {
    "truck_share": 0.267,
    "trailer_truck_share": 0.733,
    "truck_avg_load": 4.44,
		"trailer_truck_avg_load": 22.49,
		"empty_share": 1.0
  },
  "majon": {
    "truck_share": 0.267,
    "trailer_truck_share": 0.733,
    "truck_avg_load": 4.44,
		"trailer_truck_avg_load": 22.49,
		"empty_share": 1.0
  },
  "huonek": {
    "truck_share": 0.267,
    "trailer_truck_share": 0.733,
    "truck_avg_load": 4.44,
		"trailer_truck_avg_load": 22.49,
		"empty_share": 1.0
  },
  "jate": {
    "truck_share": 0.381,
    "trailer_truck_share": 0.619,
    "truck_avg_load": 6.02,
		"trailer_truck_avg_load": 27.08,
		"empty_share": 0.5
  }
}