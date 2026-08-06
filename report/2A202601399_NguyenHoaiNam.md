# Báo cáo cá nhân — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Nguyễn Hoài Nam |
| MSSV | 2A202601399 |
| Khóa/Lớp | K3 |
| Nhóm | Nhóm 5 thành viên |
| Vai trò chính | Thành viên 1 — Ingestion owner |
| Repository | https://github.com/NguyenHoaiNam2k5/K3_Day10_Data-Pipeline-Data-Observability-C12.git |
| Ngày hoàn thành | 2026-08-06 |

## 2. Vai trò và phạm vi công việc

| Module/deliverable | File/hàm phụ trách | Input | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Parse Crossref payload | `src/ingestion/crossref.py` — `parse_crossref_payload` | JSON response từ Crossref `/works` | Danh sách `PaperRecord` hợp lệ | Hoàn thành |
| Fetch và lưu raw lineage | `crossref.py` — `fetch_source_records` | `Settings`, query/filter Crossref | `crossref_response.json`, `crossref_records.json` | Hoàn thành |
| Load raw snapshot | `crossref.py` — `load_raw_records` | Raw records JSON đã lưu | Danh sách `PaperRecord` để tái chạy/repair | Hoàn thành |
| Chuẩn hóa metadata nguồn | Các helper trong `crossref.py` | DOI, title, abstract, author, subject, dates, links | Metadata sạch ở ranh giới ingestion | Hoàn thành |

Phần ingestion là điểm đầu của pipeline. Output của phần này được bàn giao cho Cleaning/Test set ở baseline và được sử dụng lại làm nguồn tin cậy khi corruption flow repair dữ liệu. Vì vậy raw response phải được lưu nguyên trạng trước khi parse, còn raw records phải giữ schema ổn định để các module sau có thể tái lập kết quả.

## 3. Kết quả theo vai trò

| Nhiệm vụ | File/hàm/artifact | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Gọi Crossref theo query của bài lab | `fetch_source_records` | Nhận 24 items từ Crossref với query và freshness filter | Đọc `data/raw/crossref_response.json` |
| Parse dữ liệu học thuật | `parse_crossref_payload` | 24 `PaperRecord`, 24 DOI duy nhất, không có ID/title/summary rỗng | Đọc `data/raw/crossref_records.json` |
| Bảo toàn raw lineage | `data/raw/` | Lưu cả response gốc và records sau parse | Kiểm tra hai JSON trong `data/raw/` |
| Hỗ trợ chạy offline/tái lập | `load_raw_records` | Nạp lại snapshot khi `REFRESH_SOURCE` không bật | Chạy Phase 1 với raw snapshot hiện có |
| Cung cấp nguồn cho repair | `crossref_records.json` | Corruption flow dựng lại 24 repaired records/24 ID duy nhất | Đọc `papers_clean_repaired.json` và comparison report |

Artifact tiêu biểu là `data/raw/crossref_response.json`: đây là response thành công được ghi xuống đĩa trước mọi bước parse/transform. File `crossref_records.json` là contract trung gian gồm 24 records có các trường cố định của `PaperRecord`. Baseline đọc 24 raw records và tạo 24 clean records; repair cũng đọc lại chính snapshot này và phục hồi dataset từ 23 corrupted rows/20 ID duy nhất về 24 rows/24 ID duy nhất.

## 4. Giải thích kỹ thuật

### Vấn đề cần giải quyết

Crossref trả về payload lồng nhau và metadata không đồng nhất giữa các nhà xuất bản: title có thể nằm trong list, abstract có JATS/XML, author có thể dùng `given`/`family` hoặc `name`, ngày có nhiều nguồn và độ chi tiết khác nhau, còn PDF URL không phải item nào cũng có. Ngoài ra API có thể trả rate limit hoặc lỗi máy chủ tạm thời. Ingestion cần chuyển dữ liệu đó sang một schema ổn định mà vẫn giữ được raw evidence để audit và repair.

### Cách triển khai

`parse_crossref_payload` duyệt `payload["message"]["items"]`, lấy DOI làm `paper_id`, chuẩn hóa title/abstract và bỏ record thiếu DOI, title hoặc summary. Hàm dùng `seen_ids` để loại DOI trùng ngay tại ranh giới ingestion. Abstract ưu tiên trường `abstract` và fallback sang `description`; JATS/HTML được bỏ bằng regex rồi decode HTML entities và chuẩn hóa khoảng trắng.

Tác giả được tạo từ `name` hoặc ghép `given` và `family`. Subject trở thành `categories`; category đầu tiên được dùng làm `primary_category`. Ngày xuất bản ưu tiên lần lượt `published-print`, `published-online`, `published`, `issued`, `created`; ngày cập nhật dùng `indexed` hoặc `deposited`. `_crossref_date` hỗ trợ cả `date-time` và `date-parts`. URL bài viết lấy từ `URL` hoặc `resource.primary.URL`; PDF được chọn từ `link` có content type `application/pdf` hoặc hậu tố `.pdf`.

`fetch_source_records` gọi `https://api.crossref.org/works` với query, filter và `rows=24`. Request có timeout 30 giây và tối đa 5 attempts cho 429/500/502/503/504 hoặc lỗi timeout/kết nối. Backoff ưu tiên header `Retry-After`; nếu không có thì dùng exponential backoff 1, 2, 4, 8 giây cộng jitter nhỏ. Response bytes được lưu trước khi gọi `response.json()`, nhờ đó vẫn có bằng chứng nếu payload lỗi parse.

`load_raw_records` xác minh JSON là list, từng item là object và có đủ field của dataclass. Hàm map lại `authors`/`categories` thành list rồi tạo `PaperRecord`; nếu thiếu field sẽ báo rõ index và danh sách field thiếu.

| Thành phần | Mô tả |
| --- | --- |
| Input | Crossref `/works` response hoặc `data/raw/crossref_records.json` |
| Output | `list[PaperRecord]`, raw response JSON, raw records JSON |
| Module phụ thuộc | `core.config`, `core.utils`, `requests` |
| Module sử dụng output | `ingestion.cleaning`, `pipelines.phase1`, `pipelines.corruption_flow` |
| Lỗi cần xử lý | Network timeout, 429/5xx, malformed payload, thiếu DOI/title/abstract, metadata khác format |

### Cách xác minh

```powershell
uv run python script/run_phase1.py

$raw = Get-Content -Raw -Encoding utf8 data/raw/crossref_records.json | ConvertFrom-Json
$raw.Count
($raw.paper_id | Sort-Object -Unique).Count
($raw | Where-Object { [string]::IsNullOrWhiteSpace($_.paper_id) }).Count
```

- Kết quả thực tế: `24`, `24`, `0` — có 24 records, 24 DOI duy nhất và không có `paper_id` rỗng.
- Phase 1 hoàn thành và tạo `data/reports/phase1_report.md`; report ghi `fetched_records=24`, `cleaned_records=24`.
- Corruption flow hoàn thành; repaired dataset lấy lại từ raw snapshot có 24 rows và quality status PASS.

## 5. Quyết định kỹ thuật quan trọng

- **Bối cảnh:** Pipeline cần vừa có dữ liệu chuẩn hóa cho module sau, vừa có bằng chứng nguồn và khả năng repair sau sự cố dữ liệu.
- **Phương án cân nhắc:** chỉ lưu records đã parse; hoặc lưu cả raw response trước parse và snapshot records theo data contract.
- **Phương án chọn:** lưu hai lớp artifact: response bytes nguyên bản và danh sách `PaperRecord` đã chuẩn hóa.
- **Lý do:** Raw response hỗ trợ audit/debug parser; records snapshot giúp chạy lại pipeline không phụ thuộc mạng và là nguồn đáng tin cậy để repair.
- **Bằng chứng:** Baseline và repair đều dùng `data/raw/crossref_records.json`; repaired metrics khôi phục đúng baseline: hit rate 1.0000, token F1 0.7573, judge accuracy 0.6667 và judge score 4.0000.

Quyết định thứ hai là dùng DOI làm stable `paper_id`. DOI tồn tại xuyên suốt raw → clean → Chroma metadata → `ground_truth_doc_ids`, nhờ đó retrieval hit có thể đối chiếu trực tiếp và corruption/repair có cùng khóa nhận diện.

## 6. Blocker đã xác định

- **Triệu chứng:** 24/24 clean records có `categories` rỗng, vì vậy test set chỉ có các loại `summary`, `authors`, `date` và không tạo câu hỏi `categories`.
- **Nguyên nhân gốc:** Các Crossref items trong snapshot không cung cấp `subject`; ingestion giữ đúng dữ liệu nguồn thay vì tự suy diễn category.
- **Phạm vi ảnh hưởng:** Metadata index nghèo hơn và evaluation không đo khả năng trả lời category.
- **Cách xử lý hiện tại:** Cho phép `categories=[]` vì trường này không bắt buộc; `text_for_embedding` vẫn có title, abstract và authors nên index hoạt động.
- **Bước tiếp theo:** Có thể bổ sung nguồn taxonomy đáng tin cậy hoặc query/sample khác có subject; sau đó đo category coverage và tạo lại test set có kiểm soát.
- **Điều học được:** Không nên bịa metadata để làm schema có vẻ đầy đủ; giá trị thiếu phải được giữ minh bạch và phản ánh trong observability/report.

## 7. Hiểu biết về luồng end-to-end

1. Ingestion gọi Crossref, lưu raw response trước parse và chuyển payload thành `PaperRecord` có DOI ổn định.
2. Cleaning chuẩn hóa fields, tính `age_days`, tạo `text_for_embedding` và lưu clean CSV/JSON.
3. MiniLM mã hóa văn bản; ChromaDB lưu vector cùng DOI/title/metadata để semantic search và exact lookup.
4. Test set lấy ground truth từ clean data và dùng `paper_id` làm `ground_truth_doc_ids`. Evaluation tính retrieval hit rate, token F1 và LLM judge metrics.
5. Observability kiểm tra schema, completeness, uniqueness, validity và freshness; reporting tổng hợp metrics cùng quality signals.
6. Corruption làm mất/hỏng một phần clean data và rebuild index riêng. Repair không sửa trực tiếp corrupted rows mà nạp lại raw snapshot do ingestion cung cấp, re-clean, re-index và đánh giá trên cùng test set.
7. Việc repaired metrics trở lại đúng baseline chứng minh raw lineage đủ để phục hồi dữ liệu và hành vi pipeline trong lần chạy này.

## 8. Phân tích kết quả

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.0000 | 0.8333 | 1.0000 | Repair từ raw snapshot phục hồi đủ 3 retrieval misses |
| `mean_token_f1` | 0.7573 | 0.5178 | 0.7573 | Phục hồi toàn bộ mức giảm 0.2395 |
| `judge_accuracy` | 0.6667 | 0.5000 | 0.6667 | 12/18 → 9/18 → 12/18 |
| `mean_judge_score` | 4.0000 | 3.3889 | 4.0000 | Phục hồi toàn bộ mức giảm 0.6111 |
| Quality checks | PASS | FAIL | PASS | Raw snapshot khôi phục completeness/uniqueness/validity |
| Freshness status | Fresh | Not fresh | Fresh | Latest date và 4 ngày lỗi được phục hồi |

Vai trò ingestion thể hiện rõ nhất ở bước repair: corruption xóa 4 records mới nhất, thêm 3 ID trùng và làm hỏng summary/title/date, nhưng flow không cố vá từng lỗi trên corrupted dataset. Thay vào đó, nó nạp lại 24 `PaperRecord` từ snapshot, chạy cleaning contract và tạo repaired dataset 24 rows/24 ID. Cả quality/freshness lẫn bốn agent metrics trở lại đúng baseline, cho thấy raw artifacts có giá trị thực tế cho recovery chứ không chỉ để lưu trữ.

Một ví dụ cụ thể là record `10.2118/234689-pa` bị drop trong corruption, làm ba câu `q000`–`q002` mất retrieval hit. Khi repair đọc lại raw snapshot, DOI và toàn bộ metadata của record này xuất hiện lại trong `papers-repaired`, giúp retrieval hit rate trở về 1.0000.

## 9. Điều học được và hướng cải thiện

1. Raw response và parsed snapshot phục vụ hai mục đích khác nhau: response để audit parser, snapshot để tái lập và repair.
2. Stable ID từ nguồn là contract quan trọng nối ingestion với cleaning, indexing và evaluation.
3. Retry/backoff cần xử lý cả HTTP status lẫn lỗi kết nối, đồng thời vẫn phải lưu evidence của response thành công.

Nếu có thêm thời gian, tôi sẽ bổ sung unit tests bằng payload fixture cho các trường hợp abstract JATS, author chỉ có `name`, date thiếu tháng/ngày, nhiều PDF links, DOI trùng và item thiếu field. Tiêu chí là parser trả đúng schema/số records mà không cần gọi mạng. Tôi cũng sẽ truyền raw DataFrame vào quality suite để `source_reconciliation` chuyển từ `SKIPPED` sang `PASS` và báo chính xác raw/clean lineage.

## 10. Cam kết

- [x] Nội dung phản ánh đúng phần Ingestion tôi phụ trách.
- [x] Tôi có thể giải thích luồng end-to-end.
- [x] Kết quả và metrics được đối chiếu với artifact runtime.
- [x] Báo cáo không chứa secret.
- [x] Báo cáo không sao chép báo cáo nhóm hoặc báo cáo của thành viên khác.

**Họ và tên:** Nguyễn Hoài Nam  
**Ngày xác nhận:** 2026-08-06
