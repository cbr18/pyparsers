import { Component, OnInit } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { CommonModule } from '@angular/common';

interface Car {
  image?: string;
  title?: string;
  sh_price?: string;
  car_year?: string;
  car_mileage?: string;
  car_source_city_name?: string;
  brand_name?: string;
  series_name?: string;
  car_name?: string;
  car_source_type?: string;
  transfer_cnt?: string;
}

@Component({
  selector: 'app-car-list',
  templateUrl: './car-list.html',
  styleUrl: './car-list.scss',
  standalone: true,
  imports: [CommonModule]
})
export class CarList implements OnInit {
  cars: Car[] = [];
  loading = true;
  placeholder = 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="120" height="80"><rect width="100%" height="100%" fill="%23ccc"/><text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" fill="%23666" font-size="16">Нет фото</text></svg>';

  constructor(private http: HttpClient) {}

  ngOnInit(): void {
    window.onerror = function (message, source, lineno, colno, error) {
      alert('JS Error: ' + message);
    };
    window.onunhandledrejection = function (e) {
      alert('Promise Error: ' + e.reason);
    };
    this.http.get<any>('/cars').subscribe({
      next: (data) => {
        this.cars = data?.data?.search_sh_sku_info_list ?? [];
        this.loading = false;
      },
      error: () => {
        this.loading = false;
        alert('Ошибка загрузки данных');
      }
    });
  }

  onImgError(event: Event) {
    const img = event.target as HTMLImageElement | null;
    if (img) {
      img.src = this.placeholder;
    }
  }
}
