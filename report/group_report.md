# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin       | Nội dung                                                                          |
| --------------- | --------------------------------------------------------------------------------- |
| Khóa/Lớp        | K3                                                                                |
| Tên nhóm        | Nhóm 5 thành viên                                                                 |
| Repository      | https://github.com/NguyenHoaiNam2k5/K3_Day10_Data-Pipeline-Data-Observability-C12 |
| Ngày hoàn thành | 2026-08-06                                                                        |

### Thành viên và phân công

| STT | Họ và tên         | MSSV        | Vai trò chính                  | Module/deliverable sở hữu                                        |
| --: | ----------------- | ----------- | ------------------------------ | ---------------------------------------------------------------- |
|   1 | Nguyễn Hoài Nam   | 2A202601399 | Ingestion owner                | `src/ingestion/crossref.py`, `data/raw/`                         |
|   2 | Lâm Thành Bảo     | 2A202601719 | Cleaning & test-set owner      | `src/ingestion/cleaning.py`, `src/evaluation/testset.py`         |
|   3 | Đinh Văn Sinh     | 2A202601613 | Observability owner            | `src/observability/quality.py`, `src/observability/reporting.py` |
|   4 | Trần Anh Vân      | 2A202601513 | Corruption owner               | `src/ingestion/corruption.py`                                    |
|   5 | Ngô Hoàng Gia Bảo | 2A202601375 | Pipeline integration & release | `src/pipelines/`, báo cáo tích hợp                               |

> TODO: Nhóm xác nhận lại họ tên có dấu, MSSV, thứ tự thành viên và tên thành viên 5. Phân công trên được suy ra từ lịch sử commit và báo cáo cá nhân hiện có.

## 2. Tóm tắt kết quả

Nhóm đã hoàn thành pipeline end-to-end gồm ingestion từ Crossref, cleaning, tạo test set, embedding/index ChromaDB, evaluation, observability, corruption, repair và báo cáo so sánh. Baseline tạo 24 raw/clean records, collection `papers-baseline` gồm 24 documents và test set cố định 18 câu. Baseline đạt retrieval hit rate 1.0000, mean token F1 0.7573, judge accuracy 0.6667 và mean judge score 4.0000; toàn bộ quality checks đạt yêu cầu và dữ liệu được đánh giá Fresh. Corruption dùng seed 42, xóa 4 records mới nhất, làm rỗng 3 summaries, gây nhiễu 4 summaries, cắt 3 titles, sửa 4 ngày và thêm 3 dòng trùng. Dataset corrupted còn 23 rows/20 ID duy nhất, quality và freshness đều fail; retrieval hit rate giảm 0.1667, token F1 giảm 0.2395, judge accuracy giảm 0.1667 và judge score giảm 0.6111. Repair dựng lại dữ liệu từ raw snapshot, khôi phục 24 rows/24 ID, build collection `papers-repaired` và phục hồi toàn bộ bốn metrics đúng bằng baseline. Giới hạn chính còn lại là corpus/test set nhỏ, 24/24 records thiếu category, Ragas chưa chạy và hai check source/evaluation trong quality suite đang bị skip do pipeline chưa truyền các input tùy chọn.

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
Crossref REST API
    -> raw response + 24 parsed records
    -> cleaning/data contract -> 24 clean records
    -> MiniLM embeddings + ChromaDB papers-baseline
    -> fixed 18-question evaluation set
    -> baseline metrics + quality/freshness + phase-1 report
    -> seeded corruption -> 23 rows -> papers-corrupted
    -> corrupted metrics + quality/freshness
    -> repair from raw snapshot -> 24 rows -> papers-repaired
    -> repaired metrics + comparison report
```

### Trách nhiệm của từng khối

| Khối              | Input                      | Xử lý chính                                                             | Output/artifact                                            | Owner               |
| ----------------- | -------------------------- | ----------------------------------------------------------------------- | ---------------------------------------------------------- | ------------------- |
| Ingestion         | Crossref `/works`          | Query, retry tối đa 5 lần, parse DOI/metadata, lưu response trước parse | `data/raw/crossref_response.json`, `crossref_records.json` | Nguyễn Hoài Nam     |
| Cleaning          | Raw `PaperRecord`          | Bỏ HTML, chuẩn hóa khoảng trắng/ngày, bỏ thiếu ID/title, khử trùng ID   | `data/clean/papers_clean.{json,csv}`                       | Lâm Thành Bảo       |
| Embedding/index   | Ba dataset                 | MiniLM normalized embeddings, Chroma cosine search                      | Ba manifest trong `data/embeddings/`, `data/chroma/`       | TODO                |
| Evaluation        | Test set và ba index       | Retrieval hit, token F1, LLM judge                                      | Ba metrics và ba answers JSON                              | TODO                |
| Observability     | Ba DataFrame               | Completeness, uniqueness, validity, freshness                           | `data/quality/*.json`, Markdown reports                    | Đinh Văn Sinh       |
| Corruption/repair | Clean dataset/raw snapshot | Sáu corruption có seed; repair bằng re-clean raw snapshot               | Corrupted/repaired datasets và log                         | Trần Anh Vân / TODO |
| Orchestration     | Các module trên            | Điều phối hai flow và sinh báo cáo                                      | `data/reports/phase1_report.md`, `corruption_report.md`    | TODO                |

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình             | Giá trị sử dụng                          |
| ------------------------- | ---------------------------------------- |
| `LLM_PROVIDER`            | `openai`                                 |
| `LLM_MODEL`               | `gpt-4o-mini`                            |
| Embedding model           | `sentence-transformers/all-MiniLM-L6-v2` |
| Số lượng Crossref records | 24                                       |
| Retrieval `top_k`         | 4                                        |
| Freshness threshold       | 180 ngày                                 |
| Random seed               | 42                                       |

### Lệnh cài đặt và chạy

```powershell
uv sync
uv run python script/run_phase1.py
uv run python script/run_corruption_flow.py
```

### Kết quả tái hiện ngày 2026-08-06

| Lệnh              | Trạng thái | Thời điểm artifact cuối | Bằng chứng                                                                             |
| ----------------- | ---------- | ----------------------- | -------------------------------------------------------------------------------------- |
| Baseline pipeline | Thành công | 11:53:49                | `baseline_metrics.json`, quality/freshness JSON, `phase1_report.md`                    |
| Corruption flow   | Thành công | 12:09:23                | Corrupted/repaired datasets, metrics, quality/freshness, log và `corruption_report.md` |

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính           | Giá trị                                                                                                                                                          |
| -------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Source               | Crossref REST API, `https://api.crossref.org/works`                                                                                                              |
| Query/filter         | `query=agentic retrieval augmented generation large language model`; `from-pub-date:2026-02-07,has-abstract:true`; `rows=24`                                     |
| Thời điểm snapshot   | 2026-08-06 10:57:04                                                                                                                                              |
| Số record nhận được  | 24                                                                                                                                                               |
| Cơ chế retry/backoff | Tối đa 5 lần cho 429/500/502/503/504 và lỗi timeout/kết nối; ưu tiên `Retry-After`, nếu thiếu dùng exponential backoff 1/2/4/8 giây cộng jitter; timeout 30 giây |

### Raw và clean schema

| Trường                 | Kiểu         | Bắt buộc?       | Ý nghĩa                          | Xử lý khi thiếu/sai                                                        |
| ---------------------- | ------------ | --------------- | -------------------------------- | -------------------------------------------------------------------------- |
| `paper_id`             | string       | Có              | DOI ổn định/document ID          | Bỏ record nếu thiếu; khử trùng theo ID                                     |
| `title`                | string       | Có              | Tiêu đề bài báo                  | Bỏ HTML/chuẩn hóa; bỏ record nếu rỗng                                      |
| `summary`              | string       | Có ở bước parse | Abstract/mô tả                   | Bỏ record raw nếu thiếu; làm sạch HTML                                     |
| `authors`              | list[string] | Không           | Danh sách tác giả                | Chuẩn hóa và bỏ phần tử rỗng                                               |
| `categories`           | list[string] | Không           | Crossref subjects                | Danh sách rỗng nếu nguồn thiếu; 24/24 clean records hiện không có category |
| `published`, `updated` | string ngày  | Không           | Ngày xuất bản/cập nhật           | Chuẩn hóa `YYYY`, `YYYY-MM`, `YYYY-MM-DD` về `YYYY-MM-DD`; sai thành rỗng  |
| `age_days`             | integer/null | Không           | Tuổi bài báo tại thời điểm clean | Tính `run_date - published`; null nếu ngày không hợp lệ                    |
| `text_for_embedding`   | string       | Có cho index    | Văn bản đưa vào embedding        | Ghép title, abstract, authors và categories                                |

### Quy tắc cleaning

| Quy tắc                                            | Quality dimension     | Số record bị tác động | Cách xác minh                              |
| -------------------------------------------------- | --------------------- | --------------------: | ------------------------------------------ |
| Bỏ record thiếu `paper_id`/title/summary khi parse | Completeness/validity |                     0 | Đối chiếu raw response và records snapshot |
| Khử trùng `paper_id`                               | Uniqueness            |                     0 | 24 ID duy nhất trong clean JSON            |
| Bỏ HTML, chuẩn hóa khoảng trắng và ngày            | Validity/consistency  |                    10 | Đối chiếu raw và clean theo `paper_id`     |
| Bỏ clean record thiếu title/ID                     | Completeness          | 0 (raw 24 → clean 24) | `papers_clean.json`                        |

`text_for_embedding` có dạng `Title: ...`, `Abstract: ...`, `Authors: ...`, `Categories: ...`. Document ID dùng DOI trong `paper_id`; Chroma record ID là `<paper_id>::<row_index>`. `age_days` là số ngày từ ngày xuất bản đã chuẩn hóa đến `run_date` của bước cleaning.

## 6. Evaluation setup

| Thành phần                            | Cấu hình thực tế                                                                                      |
| ------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| Số câu hỏi                            | 18                                                                                                    |
| Các `question_type`                   | `summary` (6), `authors` (6), `date` (6)                                                              |
| Ground-truth document ID              | Lấy trực tiếp từ `paper_id` của clean row được chọn                                                   |
| Embedding model                       | `sentence-transformers/all-MiniLM-L6-v2`                                                              |
| Vector store/collection               | ChromaDB cosine: `papers-baseline` (24), `papers-corrupted` (23), `papers-repaired` (24)              |
| Retrieval `top_k`                     | 4                                                                                                     |
| LLM provider/model                    | `openai` / `gpt-4o-mini`                                                                              |
| Test set dùng chung cho ba trạng thái | `data/eval/test_set.json`, SHA-256 `A2ADF02D89BCFEBB729C35DA08195DE0EC6ED488BCA7FCF9A9CB19D346F070D2` |

Test set được tạo từ clean baseline rồi giữ nguyên cho cả ba lượt đánh giá. Việc cố định question, ground truth và ground-truth document ID giúp delta metrics phản ánh thay đổi dữ liệu/index thay vì thay đổi độ khó của bộ câu hỏi.

## 7. Kết quả baseline

### Artifact checklist

| Artifact                 | Đường dẫn thực tế                                                     | Trạng thái | Ghi chú                           |
| ------------------------ | --------------------------------------------------------------------- | ---------- | --------------------------------- |
| Raw response/records     | `data/raw/`                                                           | Có         | Response và 24 parsed records     |
| Cleaned dataset          | `data/clean/`                                                         | Có         | JSON và CSV, 24 rows              |
| Embedding manifest/index | `data/embeddings/papers_embeddings.json`, `data/chroma/`              | Có         | `papers-baseline`, 24 documents   |
| Evaluation set           | `data/eval/test_set.json`                                             | Có         | 18 câu                            |
| Baseline answers/metrics | `data/results/baseline_{answers,metrics}.json`                        | Có         | 18 samples                        |
| Quality/freshness        | `data/quality/baseline-quality_quality.json`, `freshness_report.json` | Có         | Overall PASS, Fresh               |
| Baseline report          | `data/reports/phase1_report.md`                                       | Có         | Khớp metrics và quality artifacts |

### Baseline metrics

| Metric               |  Giá trị | Diễn giải                                                             |
| -------------------- | -------: | --------------------------------------------------------------------- |
| `retrieval_hit_rate` |   1.0000 | Cả 18/18 câu truy hồi được ground-truth document trong top 4          |
| `mean_token_f1`      |   0.7573 | Mức trùng token trung bình giữa answer và ground truth                |
| `judge_accuracy`     |   0.6667 | 12/18 câu được judge đánh giá đúng                                    |
| `mean_judge_score`   | 4.0000/5 | Điểm judge trung bình                                                 |
| Ragas                |      N/A | Đã skip; artifact ghi `Set RUN_RAGAS=1` để bật lượt đánh giá chậm hơn |

Theo loại câu hỏi, authors và date đều đạt hit/F1/accuracy bằng 1.0000; nhóm summary đạt hit 1.0000 nhưng mean F1 chỉ 0.2719 và judge accuracy 0.0000. Điều này cho thấy retrieval đúng chưa bảo đảm câu trả lời tóm tắt đủ nội dung.

## 8. Data quality và freshness

### Quality checks baseline

| Check                                   | Quality dimension       | Ngưỡng/kỳ vọng                | Kết quả baseline                   | Bằng chứng                                                          |
| --------------------------------------- | ----------------------- | ----------------------------- | ---------------------------------- | ------------------------------------------------------------------- |
| Schema/row count                        | Validity/volume         | Đủ 5 cột bắt buộc; rows > 0   | PASS: đủ cột, 24 rows              | `baseline-quality_quality.json`                                     |
| `paper_id` complete/unique              | Completeness/uniqueness | 0 rỗng, 0 trùng               | PASS: 0 rỗng, 0 duplicate IDs      | Cùng artifact                                                       |
| Title/summary complete                  | Completeness            | 0 rỗng                        | PASS: 0 title rỗng, 0 summary rỗng | Cùng artifact                                                       |
| Summary minimum length                  | Validity                | Ít nhất 20 ký tự              | PASS: 0 short summaries            | Cùng artifact                                                       |
| Embedding text complete                 | Completeness            | 0 rỗng                        | PASS: 0                            | Cùng artifact                                                       |
| Published/age valid                     | Validity                | 0 ngày/tuổi lỗi               | PASS: 0/0                          | Cùng artifact                                                       |
| Freshness                               | Timeliness              | 0 rows > 180 ngày, 0 ngày lỗi | PASS                               | Cùng artifact                                                       |
| Source reconciliation/evaluation schema | Lineage/validity        | Có input kiểm tra             | SKIPPED                            | Pipeline không truyền `raw_records` và `eval_set` vào quality suite |

### Freshness

| Thuộc tính                | Baseline   | Corrupted  | Repaired   |
| ------------------------- | ---------- | ---------- | ---------- |
| Timestamp mới nhất        | 2026-08-01 | 2026-07-03 | 2026-08-01 |
| Timestamp cũ nhất hợp lệ  | 2026-02-12 | 2026-02-12 | 2026-02-12 |
| Min/max `age_days` hợp lệ | 5/175      | 34/175     | 5/175      |
| Stale rows (`> 180`)      | 0          | 0          | 0          |
| Invalid published rows    | 0          | 4          | 0          |
| Tổng rows                 | 24         | 23         | 24         |
| Trạng thái                | Fresh      | Not fresh  | Fresh      |

Corrupted freshness fail do 4 giá trị ngày bị coi là không hợp lệ, dù `stale_rows=0`. Repair phục hồi cả bốn ngày và trạng thái Fresh.

## 9. Corruption scenarios và repair

| Corruption     | Cách tạo                               | Record bị tác động | Quality/agent signal thực tế                                                                                                    | Cách repair                           |
| -------------- | -------------------------------------- | -----------------: | ------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------- |
| Drop latest    | Xóa 15% record mới nhất                |                  4 | Rows nền 24 → trung gian 20; latest date 2026-08-01 → 2026-07-03; ba câu SafeRAG mất retrieval hit                              | Re-clean raw snapshot                 |
| Blank summary  | Xóa summary của 15% rows còn lại       |                  3 | `summary_complete` và `summary_min_length` FAIL, 3 blanks/shorts                                                                | Khôi phục summary từ raw              |
| Summary noise  | Thay phần giữa abstract bằng token lỗi |                  4 | Nội dung semantic bị hỏng; ảnh hưởng gộp thể hiện ở token F1 giảm 0.2395                                                        | Khôi phục summary từ raw              |
| Truncate title | Chỉ giữ hai từ đầu                     |                  3 | Exact-title lookup hỏng; paper `10.55041/isjem07213` vẫn nằm trong top 4 nhưng không đứng đầu, làm câu authors/date trả lời sai | Khôi phục title từ raw                |
| Stale date     | Trừ 5/8/10/15 năm                      |                  4 | `published_valid`, `age_days_valid`, freshness FAIL với 4 invalid rows                                                          | Chuẩn hóa lại ngày từ raw             |
| Duplicate rows | Sao chép 15% rows                      |                  3 | Dataset cuối 23 rows/20 ID; 3 duplicate IDs và 6 duplicate rows                                                                 | Re-clean và khử trùng theo `paper_id` |

Corruption log:

- Đường dẫn: `data/results/corruption_log.json`
- Trạng thái: Có
- Tham số: seed 42, run date `2026-08-06T00:00:00+00:00`, `allow_overlap=false`
- Nhận xét: Log lưu đủ sáu operations, số lượng và danh sách record, before/after cùng validation summary.

Repair nạp lại `data/raw/crossref_records.json`, chạy lại đúng cleaning contract, lưu 24 repaired rows, build collection `papers-repaired` và đánh giá trên test set baseline cố định. Do đó recovery dựa trên nguồn snapshot có lineage, không phải sửa quality flag hoặc dùng lại index baseline.

## 10. So sánh baseline, corrupted và repaired

| Metric/signal        | Baseline |       Corrupted | Repaired |                   Thay đổi do corruption |      Mức phục hồi | Nhận xét                                            |
| -------------------- | -------: | --------------: | -------: | ---------------------------------------: | ----------------: | --------------------------------------------------- |
| `retrieval_hit_rate` |   1.0000 |          0.8333 |   1.0000 |                                  -0.1667 |    +0.1667 (100%) | Mất 3/18 hits rồi phục hồi đủ                       |
| `mean_token_f1`      |   0.7573 |          0.5178 |   0.7573 |                                  -0.2395 |    +0.2395 (100%) | Giảm mạnh nhất trong bốn metrics                    |
| `judge_accuracy`     |   0.6667 |          0.5000 |   0.6667 |                                  -0.1667 |    +0.1667 (100%) | 12/18 → 9/18 → 12/18                                |
| `mean_judge_score`   |   4.0000 |          3.3889 |   4.0000 |                                  -0.6111 |    +0.6111 (100%) | Phục hồi đúng baseline                              |
| Quality checks       |     PASS | FAIL (6 checks) |     PASS |                6 checks chuyển sang FAIL | 6/6 checks (100%) | Uniqueness, summary, date/age và freshness phục hồi |
| Freshness status     |    Fresh |       Not fresh |    Fresh | 4 invalid dates, latest date lùi 29 ngày |              100% | 0 invalid dates sau repair                          |

Hai chuỗi nhân quả có bằng chứng:

1. Xóa record `10.2118/234689-pa` → ba câu `q000`–`q002` mất ground-truth retrieval hit → retrieval hit rate giảm từ 1.0000 xuống 0.8333; authors/date token F1 của paper này giảm từ 1.0000 xuống 0.0000.
2. Cắt title và nhân đôi `10.55041/isjem07213` → exact lookup bằng full title thất bại, document đích chỉ đứng thứ hai trong semantic results → câu authors/date `q013`–`q014` lấy metadata của document đứng đầu và F1 giảm 1.0000 xuống 0.0000. Repair từ raw khôi phục full title/ID duy nhất → repaired metrics trở lại đúng baseline.

Ngoài ra, bốn ngày bị sửa làm quality/freshness fail; repair đưa invalid dates từ 4 về 0 và trạng thái Not fresh về Fresh.

## 11. Vấn đề tích hợp quan trọng

- **Triệu chứng:** Corruption “stale date” tạo bốn ngày cũ nhưng report ghi `stale_rows=0`, đồng thời `published_valid`, `age_days_valid` và freshness đều fail với 4 invalid rows.
- **Nguyên nhân:** Corruption ghi ngày dạng ISO timestamp có timezone (`YYYY-MM-DDT00:00:00+00:00`) vào cột vốn dùng chuỗi `YYYY-MM-DD`. Khi DataFrame trộn hai format, `pandas.to_datetime(..., errors="coerce")` theo suy luận format thống nhất biến bốn timestamp khác format thành `NaT`; vì vậy chúng được đếm là invalid thay vì stale.
- **Cách xử lý hiện tại:** Repair dựng lại dữ liệu từ raw snapshot nên ngày trở lại `YYYY-MM-DD`, đưa invalid count về 0 và freshness về PASS.
- **Cải thiện đề xuất:** Corruption nên ghi `new_published.date().isoformat()` hoặc quality parser dùng `format="mixed"`; thêm test yêu cầu bốn stale rows được tính vào `stale_rows` thay vì `invalid_published_rows`.
- **Cách xác minh:** Chạy lại corruption flow và kiểm tra `corruption_log.json`, `corrupted-quality_quality.json`, `corrupted_freshness.json`; kỳ vọng `stale_rows=4`, `invalid_published_rows=0` sau khi sửa.

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại                                    | Ảnh hưởng                                               | Hướng cải thiện có thể kiểm chứng                                                                            |
| ---------------------------------------------------- | ------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| Stale-date corruption sinh format ngày khác contract | Quality nhận 4 invalid rows thay vì 4 stale rows        | Chuẩn hóa output corruption hoặc parse mixed format; thêm regression test                                    |
| Source reconciliation và evaluation checks bị skip   | Chưa chứng minh lineage/test IDs trong quality artifact | Truyền raw DataFrame và eval DataFrame vào `run_data_quality_checks`; yêu cầu các check PASS thay vì SKIPPED |
| Clean data có 24/24 category rỗng                    | Không có câu hỏi category; metadata nghèo               | Bổ sung category fallback hoặc ghi contract cho phép rỗng, rồi đo coverage                                   |
| Summary answers yếu dù retrieval đúng                | Baseline summary F1 0.2719, judge accuracy 0            | Trả lời bằng đoạn tóm tắt đầy đủ hơn hoặc dùng generation có context; đo lại theo question type              |
| Corpus/test set nhỏ và lấy tại một thời điểm         | Kết quả khó khái quát                                   | Tăng corpus/test set, khóa snapshot/hash và báo cáo confidence interval                                      |
| Ragas chưa chạy                                      | Thiếu faithfulness/context metrics                      | Bật `RUN_RAGAS=1`, lưu artifact và ghi rõ provider/model                                                     |
| LLM judge có fallback heuristic                      | Metric có thể phụ thuộc availability/provider           | Ghi chế độ judge, cố định model/temperature và lưu lỗi/fallback count                                        |

## 13. Checklist trước khi nộp

- [x] Xác nhận thông tin nhóm, MSSV.
- [x] Xác nhận phân công trong bảng kiến trúc.
- [x] Hai entrypoint đã tạo đầy đủ artifact đầu ra.
- [x] Baseline, corrupted và repaired dùng cùng `data/eval/test_set.json`.
- [x] Bảng metrics khớp với các file trong `data/results/`.
- [x] Quality/freshness conclusions khớp với `data/quality/`.
- [x] Các đường dẫn báo cáo và artifact truy cập được.
- [x] Xác nhận mỗi thành viên đã hoàn thành báo cáo vai trò riêng.
- [x] Báo cáo này không chứa API key, token hoặc nội dung `.env`.
