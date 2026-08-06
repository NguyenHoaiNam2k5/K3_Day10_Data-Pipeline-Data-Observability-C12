# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin       | Nội dung                                                                              |
| --------------- | ------------------------------------------------------------------------------------- |
| Họ và tên       | Lâm Thành Bảo                                                                         |
| MSSV            | 2A202601719                                                                           |
| Khóa/Lớp        | K3                                                                                    |
| Tên nhóm        | C12                                                                                   |
| Vai trò chính   | Role 2 — Cleaning & Test Set                                                          |
| Repository      | https://github.com/NguyenHoaiNam2k5/K3_Day10_Data-Pipeline-Data-Observability-C12   |
| Ngày hoàn thành | 2026-08-06                                                                            |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable       | File/hàm phụ trách                                          | Input nhận vào                         | Output bàn giao                                      | Trạng thái  |
| ------------------------ | ----------------------------------------------------------- | -------------------------------------- | ---------------------------------------------------- | ----------- |
| Cleaning pipeline        | `src/ingestion/cleaning.py` — `build_clean_dataframe`       | `list[PaperRecord]`, `run_date`        | `pd.DataFrame` chuẩn hóa với `text_for_embedding`   | Hoàn thành  |
| Evaluation test set      | `src/evaluation/testset.py` — `build_test_set`              | `pd.DataFrame`, `output_path`          | `data/eval/test_set.json` — 18 câu hỏi 4 loại       | Hoàn thành  |

Phần việc của tôi là trung gian kết nối giữa ingestion (TV1) và toàn bộ phần sau (TV3 quality checks, TV5 evaluation). DataFrame đầu ra là input chính cho ChromaDB indexing và evaluation.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                                    | Thành viên/module được hỗ trợ | Kết quả                                                             |
| -------------------------------------------- | ----------------------------- | ------------------------------------------------------------------- |
| Test integration với raw data thật của TV1   | TV1 — `crossref.py`           | Xác nhận `load_raw_records` → `build_clean_dataframe` chạy đúng, 24 records → 18 câu hỏi |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện                     | File/hàm/artifact liên quan                     | Kết quả bàn giao                                  | Cách xác minh                                           |
| ----------------------------------------- | ----------------------------------------------- | ------------------------------------------------- | ------------------------------------------------------- |
| Implement cleaning pipeline               | `src/ingestion/cleaning.py`                     | DataFrame 24 rows, đủ cột, `text_for_embedding`  | Chạy lệnh test với mock data → 4 papers, age_days đúng  |
| Implement test set builder                | `src/evaluation/testset.py`                     | `data/eval/test_set.json` — 18 câu hỏi           | `Generated 18 test questions` khi chạy với data thật    |
| Test integration với data thật từ TV1     | `data/raw/crossref_records.json`                | Xác nhận pipeline hoạt động end-to-end            | Chạy `load_raw_records` → `build_clean_dataframe`       |

Output cụ thể: file `data/eval/test_set.json` chứa 18 câu hỏi thuộc 4 loại (`summary`, `authors`, `date`, `categories`) tạo từ 24 bài báo thật từ Crossref API, mỗi câu có `ground_truth_doc_ids` để đo retrieval hit rate.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Raw data từ Crossref API có nhiều vấn đề: abstract chứa HTML tags (`<jats:p>`), date có nhiều format (`YYYY`, `YYYY-MM`, `YYYY-MM-DD`), authors là list object phức tạp. Phần này cần chuẩn hóa tất cả thành DataFrame nhất quán để ChromaDB index được và evaluation có ground truth chính xác.

### Cách triển khai

**Cleaning (`build_clean_dataframe`):**
- Strip HTML bằng regex `<[^>]+>` trước khi xử lý text
- Parse date linh hoạt: thử lần lượt `%Y-%m-%d` → `%Y-%m` → `%Y`, chuẩn hóa về `YYYY-MM-DD`
- Tính `age_days` = `run_date - published_date` để freshness check sau này dùng
- Tạo `text_for_embedding` = `Title + Abstract + Authors + Categories` để vector search có đủ context
- Drop duplicate theo `paper_id`, filter bỏ row thiếu title, sort mới nhất lên trên

**Test set (`build_test_set`):**
- Dùng step sampling (`iloc[::step]`) để chọn papers phân bố đều, tránh chọn toàn papers cùng ngày
- Tạo 4 loại câu hỏi per paper, skip nếu field tương ứng trống để tránh ground_truth rỗng
- `ground_truth_doc_ids` = `[paper_id]` cho phép `evaluate_pipeline` tính `retrieval_hit_rate`

### Input, output và contract

| Thành phần              | Mô tả                                                                                 |
| ----------------------- | ------------------------------------------------------------------------------------- |
| Input (cleaning)        | `list[PaperRecord]` từ `crossref.py`, `run_date: datetime`                           |
| Output (cleaning)       | `pd.DataFrame` với cột: `paper_id`, `title`, `summary`, `authors_joined`, `categories_joined`, `published`, `age_days`, `summary_chars`, `text_for_embedding`, `abs_url`, `pdf_url` |
| Input (testset)         | `pd.DataFrame` từ cleaning, `output_path: Path`                                      |
| Output (testset)        | `list[dict]` ghi ra JSON: `id`, `question_type`, `question`, `ground_truth`, `ground_truth_doc_ids` |
| Module phụ thuộc        | `src/ingestion/crossref.py` (PaperRecord schema), `src/core/utils.py`               |
| Module sử dụng output   | `src/retrieval/index.py` (dùng DataFrame), `src/evaluation/metrics.py` (dùng test set JSON), `src/observability/quality.py` (dùng DataFrame) |
| Điều kiện lỗi cần xử lý | DataFrame rỗng nếu TV1 trả về records không hợp lệ; test set raise `ValueError` nếu ít hơn 4 papers |

### Cách xác minh

```bash
.venv/bin/python -c "
from core.config import load_settings
from ingestion.crossref import load_raw_records
from ingestion.cleaning import build_clean_dataframe
from evaluation.testset import build_test_set
from datetime import datetime, UTC

settings = load_settings()
records = load_raw_records(settings.paths.raw_records_json)
df = build_clean_dataframe(records, datetime.now(UTC))
print(df[['paper_id','title','age_days','summary_chars']].to_string())
items = build_test_set(df, settings.paths.eval_testset)
print(f'Generated {len(items)} test questions')
"
```

- **Kết quả mong đợi:** 24 papers được clean, in ra bảng đủ cột, sinh ≥ 16 câu hỏi.
- **Kết quả thực tế:** 24 papers sạch, `Generated 18 test questions`.
- **Artifact/log:** `data/eval/test_set.json`

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Khi tạo `text_for_embedding`, phải quyết định đưa những trường nào vào để vector search hiệu quả nhất.
- **Các phương án đã cân nhắc:**
  - Chỉ dùng `title + summary` — đơn giản nhưng mất thông tin tác giả và chủ đề.
  - Dùng `title + summary + authors + categories` — đầy đủ hơn, câu hỏi về tác giả và danh mục vẫn match được.
- **Phương án đã chọn:** `Title + Abstract + Authors + Categories`.
- **Lý do:** Test set có 4 loại câu hỏi gồm cả `authors` và `categories`. Nếu thiếu hai trường này trong embedding thì câu hỏi dạng "Who authored..." sẽ không retrieve được đúng paper, làm `retrieval_hit_rate` thấp không phản ánh đúng chất lượng data.
- **Bằng chứng:** Test set gồm 18 câu hỏi đủ 4 loại, ground_truth_doc_ids khớp với paper_id trong DataFrame.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `ModuleNotFoundError: No module named 'ingestion'` khi chạy test script.
- **Lệnh hoặc bước tái hiện:** Chạy `python -c "from ingestion.crossref import PaperRecord"` bằng Python system thay vì Python trong `.venv`.
- **Nguyên nhân gốc:** Project dùng `src` layout, package chỉ được cài vào `.venv` sau khi chạy `pip install -e .`. Python system không biết đường dẫn đến `src/`.
- **Cách xử lý:** Dùng `.venv/bin/python` thay vì `python` để chạy đúng interpreter có package đã cài.
- **Cách xác minh sau khi sửa:** `.venv/bin/python -c "from ingestion.crossref import PaperRecord; print('OK')"` → in ra `OK`.
- **Điều học được:** Với `src` layout, luôn chạy script qua interpreter của `.venv`, không dùng Python system. Lệnh `pip install -e .` cài package ở chế độ editable nên code thay đổi không cần cài lại.

## 7. Hiểu biết về luồng end-to-end

**Câu trả lời:**

1. **Crossref → vector index:** Crossref API trả về metadata bài báo dạng JSON. TV1 parse thành `list[PaperRecord]`. TV2 (cleaning) chuẩn hóa thành DataFrame với cột `text_for_embedding`. ChromaDB dùng `sentence-transformers/all-MiniLM-L6-v2` để embed cột này và lưu vector vào persistent storage. Khi có query, câu hỏi cũng được embed bằng cùng model rồi so sánh cosine similarity để lấy top-k kết quả.

2. **Evaluation set và ground-truth doc IDs:** `build_test_set` tạo câu hỏi từ DataFrame và lưu `ground_truth_doc_ids` là `[paper_id]` của paper nguồn. Khi evaluate, `evaluate_pipeline` lấy câu hỏi → RAG agent trả về danh sách `retrieved_doc_ids` → kiểm tra có `paper_id` nào trong `ground_truth_doc_ids` không → tính `retrieval_hit_rate`. `mean_token_f1` và `judge_accuracy` đo chất lượng câu trả lời so với `ground_truth`.

3. **Quality checks vs freshness monitoring:** Quality checks kiểm tra tính đúng đắn của data tại thời điểm hiện tại (null values, uniqueness, summary length). Freshness monitoring kiểm tra data có còn mới hay không theo thời gian (so sánh `age_days` với `freshness_threshold_days = 180`). Quality check phát hiện lỗi cấu trúc; freshness phát hiện data cũ không còn relevance.

4. **Cùng test set cho cả 3 trạng thái:** Nếu dùng test set khác nhau, không thể biết metrics thay đổi do data corruption hay do câu hỏi khó/dễ hơn. Cùng test set đảm bảo mọi thay đổi trong metrics chỉ đến từ chất lượng data, không phải từ evaluation set.

5. **Repair thành công dựa trên:** `repaired_metrics.json` cho thấy `retrieval_hit_rate`, `mean_token_f1`, `judge_accuracy` phục hồi về gần bằng baseline; `data/quality/` report cho thấy quality checks pass trở lại; freshness report cho thấy `is_fresh: true`.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal        | Baseline | Corrupted | Repaired | Nhận xét của cá nhân                                                                           |
| -------------------- | -------: | --------: | -------: | ---------------------------------------------------------------------------------------------- |
| `retrieval_hit_rate` |     1.00 |       [ ] |      [ ] | Baseline đạt 100% — test set và embedding khớp tốt                                             |
| `mean_token_f1`      |     0.76 |       [ ] |      [ ] | F1 khá, một số câu trả lời dài hơn ground truth nên precision thấp hơn recall                 |
| `judge_accuracy`     |     0.67 |       [ ] |      [ ] | 67% câu đúng — còn room cải thiện chất lượng text_for_embedding                               |
| `mean_judge_score`   |     3.67 |       [ ] |      [ ] | Điểm 3.67/5 — mức chấp nhận được cho baseline                                                 |
| Quality checks       |     pass |       [ ] |      [ ] | 0 stale rows, 24 records valid, is_fresh: true                                                 |
| Freshness status     |    fresh |       [ ] |      [ ] | latest: 2026-08-01, oldest: 2026-02-12, max age_days 175 < ngưỡng 180                        |

### Kết luận từ số liệu

Chờ TV5 chạy `run_corruption_flow.py` để có cột Corrupted và Repaired rồi phân tích đầy đủ.

**Baseline đáng chú ý:** `retrieval_hit_rate` đạt 1.0 nhưng `judge_accuracy` chỉ 0.67, cho thấy pipeline retrieve đúng paper nhưng câu trả lời trích xuất từ metadata chưa chính xác hoàn toàn so với ground truth. Đây là điểm sẽ bị ảnh hưởng rõ nhất khi data bị corrupt (blank summary, truncated title).

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Data pipeline:** Raw data từ API thực tế rất ít khi sạch — Crossref trả abstract có HTML tags, date có nhiều format khác nhau, authors là nested object. Cleaning phải xử lý đủ các edge case thay vì assume data đã chuẩn.

2. **Data quality/observability:** `text_for_embedding` là cột quyết định chất lượng retrieval. Nếu cleaning bỏ sót thông tin (ví dụ không đưa `authors` vào), câu hỏi dạng "Who authored..." sẽ không retrieve đúng dù model tốt. Data quality ảnh hưởng trực tiếp đến output của toàn bộ pipeline.

3. **Ảnh hưởng data đến RAG:** Cùng một test set nhưng với data corrupted (blank summary, truncated title, stale date), `retrieval_hit_rate` và `judge_accuracy` sẽ giảm rõ rệt vì vector index không còn chứa đủ thông tin để match câu hỏi đúng paper. Repair từ raw data là cách duy nhất đáng tin cậy vì không cần đoán giá trị bị mất.

### Nếu có thêm thời gian

Cải thiện `build_test_set` để dùng LLM sinh câu hỏi tự nhiên hơn thay vì template cứng ("What is the paper '...' about?"). Câu hỏi dạng template dễ bị retrieval match theo keyword thay vì semantic, làm `retrieval_hit_rate` cao giả tạo. Có thể đo bằng cách so sánh hit rate giữa template questions và LLM-generated questions trên cùng corpus.

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Lâm Thành Bảo
**Ngày xác nhận:** 2026-08-06
