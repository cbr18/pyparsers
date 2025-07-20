package domain

import "time"

// Brand — доменная модель бренда автомобиля
type Brand struct {
	ID        string     `json:"id" gorm:"primaryKey;type:uuid;default:gen_random_uuid()"`
	Name      *string    `json:"name" gorm:"type:varchar(255)"`
	OrigName  *string    `json:"orig_name" gorm:"type:varchar(255);column:orig_name"`
	CreatedAt time.Time  `json:"created_at"`
	UpdatedAt time.Time  `json:"updated_at"`
	DeletedAt *time.Time `json:"deleted_at" gorm:"index"`
}
