# Báo cáo cá nhân — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Đinh Văn Sinh |
| MSSV | 2A202601613 |
| Khóa/Lớp | K3 |
| Nhóm | Nhóm 5 thành viên |
| Vai trò chính | Thành viên 3 — Observability |
| Repository | https://github.com/NguyenHoaiNam2k5/K3_Day10_Data-Pipeline-Data-Observability-C12.git |
| Ngày hoàn thành | 2026-08-06 |

## 2. Vai trò và phạm vi công việc

| Module/deliverable | File/hàm phụ trách | Input | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Data-quality checks | `src/observability/quality.py` — `run_data_quality_checks` | `DataFrame`, `Settings`, tên report | `<report_name>_quality.json` | Hoàn thành |
| Freshness monitoring | `quality.py` — `build_freshness_report` | `DataFrame`, ngưỡng freshness, đường dẫn | JSON freshness | Hoàn thành |
| Markdown reporting | `src/observability/reporting.py` — `generate_phase1_report`, `generate_corruption_report` | Source summary, metrics, quality, freshness | Báo cáo baseline và comparison Markdown | Hoàn thành |

Phần này nhận cleaned dataset từ Cleaning/Test set và được Phase 1 hoặc Corruption flow gọi sau khi đánh giá. Các artifact quan sát là đầu vào bằng chứng cho thành viên Integration & Comparison.

## 3. Kết quả theo vai trò

| Nhiệm vụ | File/hàm/artifact | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Kiểm tra chất lượng dữ liệu | `quality.py` | Kiểm tra schema, số dòng, completeness, uniqueness, validity và freshness | Đọc JSON trong `data/quality/` |
| Tổng hợp độ mới dữ liệu | `build_freshness_report` | `latest_published`, `oldest_published`, stale/invalid rows và `is_fresh` | Đọc `data/quality/freshness_report.json` |
| Sinh báo cáo audit | `reporting.py` | Bảng metrics, quality, freshness; so sánh baseline/corrupted/repaired và delta | Đọc `data/reports/*.md` |

Artifact tiêu biểu là `data/quality/<report_name>_quality.json`: file lưu thời điểm tạo, tổng số dòng, trạng thái tổng thể và chi tiết từng check để có thể audit thay vì chỉ in log.

## 4. Giải thích kỹ thuật

### Vấn đề cần giải quyết

Pipeline RAG có thể vẫn chạy khi dữ liệu thiếu, trùng, summary quá ngắn hoặc ngày xuất bản không hợp lệ. Cần phát hiện các lỗi này và trình bày cùng metric đánh giá để xác định ảnh hưởng thực tế của dữ liệu lên agent.

### Cách triển khai

`run_data_quality_checks` yêu cầu các cột `paper_id`, `title`, `summary`, `published`, `text_for_embedding`. Hàm đếm giá trị trống sau khi chuẩn hóa chuỗi, phát hiện ID trùng nhưng bỏ qua ID rỗng, kiểm tra summary có tối thiểu 20 ký tự và parse ngày bằng `pandas.to_datetime(errors="coerce", utc=True)`.

Freshness ưu tiên cột `age_days`; nếu thiếu sẽ tính từ `published` đến `now_utc()`. Một bản ghi stale khi tuổi vượt `settings.freshness_threshold_days`; ngày không parse được cũng làm freshness fail. Các hàm không sửa `DataFrame` đầu vào. `reporting.py` chuyển boolean thành PASS/FAIL, escape ký tự Markdown trong ô bảng, và chỉ tính delta số học khi cả hai giá trị là số. Vì vậy báo cáo không suy diễn recovery nếu artifact không chứng minh được.

| Thành phần | Mô tả |
| --- | --- |
| Input | Clean/corrupted/repaired `DataFrame`; `Settings`; metric và metadata từ pipeline |
| Output | Quality JSON, freshness JSON, baseline report, corruption comparison report |
| Module phụ thuộc | `core.config`, `core.utils`, `pandas` |
| Module sử dụng output | `pipelines/phase1.py`, `pipelines/corruption_flow.py` và người review artifact |
| Lỗi cần xử lý | Thiếu cột, dữ liệu rỗng, ID trùng, summary ngắn, ngày sai/thiếu, dữ liệu stale |

### Cách xác minh

```powershell
uv run python script/run_phase1.py
uv run python script/run_corruption_flow.py
Get-Content data/quality/*_quality.json
Get-Content data/quality/freshness_report.json
Get-Content data/reports/phase1_report.md
Get-Content data/reports/corruption_report.md
```

- Kết quả mong đợi: mỗi flow tạo JSON quality/freshness và Markdown report tương ứng; report hiển thị PASS/FAIL và delta.
- Trạng thái xác minh: repository hiện chưa có artifact `data/` và hai pipeline integration vẫn là `NotImplementedError`, nên chưa có kết quả runtime/metric để khẳng định.

## 5. Quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cần vừa phát hiện lỗi dữ liệu vừa giữ báo cáo có thể kiểm chứng.
- **Phương án cân nhắc:** chỉ trả về một boolean tổng quát; hoặc lưu chi tiết từng check có số đếm và ngưỡng.
- **Phương án chọn:** JSON có trạng thái tổng thể kèm chi tiết từng check, sau đó render Markdown từ chính các artifact này.
- **Lý do:** Có thể truy vết nguyên nhân fail, so sánh giữa các trạng thái và tránh kết luận dựa trên log tạm thời.
- **Bằng chứng:** `checks` chứa `blank_count`, `duplicate_id_count`, `short_count`, `invalid_count`, `stale_rows` và `threshold_days`.

## 6. Blocker đã xác định

- **Triệu chứng:** Chạy entrypoint hiện dừng tại `NotImplementedError: Student task: implement phase1 pipeline.` hoặc corruption flow tương tự.
- **Nguyên nhân gốc:** `src/pipelines/phase1.py` và `src/pipelines/corruption_flow.py` vẫn là khung TODO, chưa gọi module observability.
- **Phạm vi ảnh hưởng:** Chưa sinh được `data/quality/` và `data/reports/` từ end-to-end flow; không có metric thực nghiệm để điền báo cáo.
- **Bước tiếp theo:** Thành viên 5 tích hợp các hàm quality, freshness và reporting đúng thứ tự sau evaluation; sau đó chạy hai lệnh ở mục 4 để kiểm chứng artifact.
- **Điều học được:** Một module observability hoàn chỉnh chỉ tạo bằng chứng runtime khi contract gọi nó được nối vào orchestration.

## 7. Hiểu biết về luồng end-to-end

1. Crossref cung cấp raw records; Cleaning chuẩn hóa và tạo `text_for_embedding`; embedding model mã hóa văn bản và ChromaDB lưu vector để truy hồi top-k.
2. Test set giữ `question`, `ground_truth` và `ground_truth_doc_ids`. Retrieval hit rate đối chiếu document truy hồi với ID ground truth; token F1 và judge metrics chấm câu trả lời với ground truth.
3. Quality checks kiểm tra tính đúng/đủ của bản ghi tại thời điểm chạy; freshness monitoring tập trung vào tuổi, ngày xuất bản hợp lệ và ngưỡng stale.
4. Cùng test set loại bỏ khác biệt do câu hỏi hoặc ground truth, nên chênh lệch baseline/corrupted/repaired chủ yếu phản ánh trạng thái dữ liệu/index.
5. Repair chỉ được xem là thành công khi repaired dataset/quality/freshness artifacts tốt hơn theo kỳ vọng và metric evaluation trên cùng test set được phục hồi; không được kết luận chỉ từ thao tác repair.

## 8. Phân tích kết quả

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | N/A | N/A | N/A | Chưa có artifact runtime |
| `mean_token_f1` | N/A | N/A | N/A | Chưa có artifact runtime |
| `judge_accuracy` | N/A | N/A | N/A | Chưa có artifact runtime |
| `mean_judge_score` | N/A | N/A | N/A | Chưa có artifact runtime |
| Quality checks | N/A | N/A | N/A | Chờ JSON quality |
| Freshness status | N/A | N/A | N/A | Chờ JSON freshness |

Chưa thể hoàn thành chuỗi nguyên nhân–bằng chứng bằng số liệu vì chưa có baseline/corrupted/repaired artifacts. Khi flow được tích hợp, corruption như blank summary, duplicate ID hoặc stale date phải được đối chiếu lần lượt với `summary_complete`/`summary_min_length`, `paper_id_unique` hoặc `freshness`, rồi mới liên hệ với metric agent trong comparison report.

## 9. Điều học được và hướng cải thiện

1. Data pipeline cần raw và JSON artifact để tái lập và audit, không chỉ cần dữ liệu cuối.
2. Observability hữu ích khi check có ngưỡng, số đếm và trạng thái rõ ràng.
3. Chất lượng RAG cần đo trên cùng test set để phân biệt ảnh hưởng dữ liệu với biến thiên đánh giá.

Nếu có thêm thời gian, tôi sẽ bổ sung test tự động cho DataFrame rỗng, thiếu cột, ngày lỗi, ID trùng và `age_days` thiếu; tiêu chí là xác nhận chính xác PASS/FAIL và các số đếm trong JSON.

## 10. Cam kết

- [x] Nội dung phản ánh đúng phần Observability tôi phụ trách.
- [x] Tôi có thể giải thích luồng end-to-end.
- [x] Không tự khẳng định metric hay runtime chưa có artifact.
- [x] Báo cáo không chứa secret.
- [x] Báo cáo không sao chép báo cáo nhóm.

**Họ và tên:** Đinh Văn Sinh
**Ngày xác nhận:** 2026-08-06
