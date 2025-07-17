package models

type Car struct {
    ID          string  `json:"id"`
    Make        string  `json:"make"`
    Model       string  `json:"model"`
    Year        int     `json:"year"`
    Price       float64 `json:"price"`
}

type Filter struct {
    Make  string `json:"make,omitempty"`
    Model string `json:"model,omitempty"`
    Year  int    `json:"year,omitempty"`
}