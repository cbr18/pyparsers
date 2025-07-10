import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { HttpClientModule } from '@angular/common/http';
import { CarList } from './car-list/car-list';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, HttpClientModule, CarList],
  templateUrl: './app.html',
  styleUrl: './app.scss'
})
export class App {
  protected title = 'telegramngapp';
}
