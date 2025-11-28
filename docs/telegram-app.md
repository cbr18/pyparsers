# Telegram Web Clients & Image Proxy

## React Telegram App (`telegramapp/`)

- Shows paginated lists of cars plus a detailed drawer.
- Filters: source, brand, city, year, free-text search.
- Tech stack: React 18 + plain CSS; `src/services/api.js` hits `/api/cars`.

### Usage
```bash
cd telegramapp
npm install
npm start          # dev on http://localhost:3000
npm run build      # production bundle (used by docker image)
```

### Data shown in the UI

**CarCard (list view)**
- Always: `image`, `title`/`car_name`, `final_price` (or `rub_price`), `year`, `brand_name`.
- When present: `mileage`, `city`, `series_name`, `car_name` (if it differs).

**CarDetails (drawer)**
- Gallery (`image_gallery` split by space), title/model/source.
- Cost breakdown: `rub_price`, `recycling_fee`, `customs_duty`, fixed fees (commission + broker).
- Brand/model metadata, year, mileage, city.
- Technical/comfort highlights: `engine_volume`, `power`, `torque`, `transmission`, `drive_type`, `fuel_type`, `fuel_consumption`, `acceleration`, `max_speed`.
- Dimensions block when at least one of `length`, `width`, `height`, `wheelbase`, `curb_weight` exists.
- Body/exterior info (color, door/seat count), owner count, emission standard, certification, description + source link.

**Hidden model fields**
- Internal IDs (`uuid`, `car_id`, `sku_id`, `shop_id`, `mybrand_id`), tagging (`tags`, `tags_v2`), counters (`view_count`, `favorite_count`), contact/dealer blobs, advanced drivetrain/electronics metadata, and various history fields remain server-side to keep the UI lean. They are available in the API if you choose to surface them later.

## Angular Client (`telegramngapp/`)

Generated with Angular CLI 20.0.5—useful for experimenting with a different UI stack.

```bash
cd telegramngapp
npm install
ng serve            # http://localhost:4200
ng build            # emits dist/ bundle
ng test             # karma tests
ng e2e              # plug your preferred runner
```

## Image Proxy

Large CDNs often reject cross-origin requests, so nginx exposes `/proxy-image/<encoded_url>`:

```nginx
location /proxy-image/ {
    rewrite ^/proxy-image/(.*)$ $1 break;
    proxy_pass $1;
    proxy_set_header Host "";
    proxy_set_header Referer "";
    proxy_set_header Origin "";
    proxy_cache static_cache;
    proxy_cache_valid 200 1h;
}
```

React components call `getProxiedImageUrl()` to wrap external URLs automatically. Supported sources:

- HTTP/HTTPS CDNs (autoimg.cn, byteimg.com, etc.)
- Relative URLs and base64 data URIs (returned untouched)
- Same-origin URLs (no rewrite)

### Testing
```bash
./test-image-proxy.sh
# or curl manually
curl -I "http://localhost/proxy-image/https%3A//autoimg.cn/example.jpg"
```

Rate limiting and cache headers ensure the proxy doesn't become a bottleneck while maintaining CORS-safe image rendering on every client.

