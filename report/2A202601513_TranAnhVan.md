# Báo cáo cá nhân — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin       | Nội dung                                                       |
| --------------- | -------------------------------------------------------------- |
| Họ và tên       | TRẦN ANH VĂN                                                   |
| MSSV            | 2A202601513                                                    |
| Khóa/Lớp        | K3                                                             |
| Nhóm            | C12                                                            |
| Vai trò chính   | Thành viên 4 — Corruption & Repair                             |
| Repository      | NguyenHoaiNam2k5/K3_Day10_Data-Pipeline-Data-Observability-C12 |
| Ngày hoàn thành | 2026-08-06                                                     |

## 2. Vai trò và phạm vi công việc

Trong bài lab Day 10, vai trò của tôi là phụ trách phần **Corruption & Repair**. Phần việc này nằm ở giai đoạn sau khi nhóm đã có baseline pipeline với dữ liệu sạch. Mục tiêu chính là giả lập các lỗi dữ liệu có chủ đích, đo tác động của lỗi đó lên hệ thống RAG, sau đó hỗ trợ quy trình repair để chứng minh pipeline có thể phục hồi từ nguồn dữ liệu gốc.

## 3. Phần việc sở hữu

| Module/deliverable         | File/hàm phụ trách                                          | Input nhận vào                            | Output bàn giao                         | Trạng thái                          |
| -------------------------- | ----------------------------------------------------------- | ----------------------------------------- | --------------------------------------- | ----------------------------------- |
| Data corruption simulation | `src/ingestion/corruption.py` / `corrupt_clean_dataframe()` | Clean dataframe từ baseline               | Corrupted dataframe                     | Hoàn thành phần thiết kế/triển khai |
| Corruption audit log       | `data/results/corruption_log.json`                          | Các record bị corrupt và loại lỗi áp dụng | Log truy vết corruption theo `paper_id` | Hoàn thành phần thiết kế/triển khai |
| Rebuild helper fields      | `summary_chars`, `age_days`, `text_for_embedding`           | Dataframe sau corruption                  | Dataframe sẵn sàng để rebuild embedding | Hoàn thành phần thiết kế/triển khai |
| Mock self-test             | `if __name__ == "__main__"` trong `corruption.py`           | Mock clean dataframe                      | Assert test và mock corruption log      | Hoàn thành phần thiết kế/triển khai |

## 4. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện                | File/hàm/artifact liên quan                       | Kết quả bàn giao                                                                             | Cách xác minh                                            |
| ------------------------------------ | ------------------------------------------------- | -------------------------------------------------------------------------------------------- | -------------------------------------------------------- |
| Thiết kế hàm tạo corrupted dataframe | `src/ingestion/corruption.py`                     | Hàm `corrupt_clean_dataframe()` không mutate dataframe gốc                                   | Chạy self-test bằng `python src/ingestion/corruption.py` |
| Giả lập nhiều loại lỗi dữ liệu       | `corrupt_clean_dataframe()`                       | Drop latest records, blank summary, inject noise, truncate title, stale date, duplicate rows | Kiểm tra `data/results/mock_corruption_log.json`         |
| Rebuild các field phục vụ downstream | `summary_chars`, `age_days`, `text_for_embedding` | Corrupted dataframe vẫn đúng schema để build embedding/index                                 | Assert trong mock tests                                  |
| Ghi corruption log                   | `data/results/corruption_log.json`                | Log có seed, run date, source row count, result row count, operations và validation summary  | Mở file JSON log để đối chiếu                            |
| Kiểm thử mock độc lập                | `if __name__ == "__main__"`                       | Có thể test module mà chưa cần chạy toàn bộ pipeline                                         | Chạy file trực tiếp và xem kết quả PASS                  |

Output quan trọng nhất của phần việc là **corrupted dataset có thể tái lập và có log truy vết rõ ràng**. Điều này giúp nhóm chứng minh dữ liệu lỗi có thể làm giảm chất lượng retrieval/answer của RAG agent, đồng thời tạo cơ sở để so sánh với repaired dataset.

## 5. Giải thích kỹ thuật

### Vấn đề cần giải quyết

Trong hệ thống RAG, chất lượng câu trả lời phụ thuộc trực tiếp vào chất lượng corpus được embed vào vector database. Nếu dữ liệu đầu vào bị mất record, summary rỗng, text nhiễu, title bị cắt, ngày xuất bản quá cũ hoặc duplicate, hệ thống retrieval có thể trả về context sai hoặc thiếu. Khi đó agent có thể trả lời thiếu chính xác dù logic agent không thay đổi.

Phần việc của tôi giải quyết bài toán này bằng cách tạo một **data incident simulation**: cố ý làm hỏng dữ liệu sạch theo cách có kiểm soát, sau đó để pipeline đo tác động bằng metrics và quality/freshness reports.

### Cách triển khai

Tôi triển khai workflow trong phạm vi `corruption.py` theo hướng thực tế hơn việc chỉ làm theo pseudo-code đơn giản:

1. Validate data contract trước khi corrupt. Hàm kiểm tra dataframe phải có tối thiểu các cột `paper_id`, `title`, `summary`, `published`.
2. Copy dataframe gốc bằng `df.copy(deep=True)` để không mutate baseline clean data.
3. Dùng seed cố định để corruption có thể tái lập giữa nhiều lần chạy.
4. Drop latest records dựa trên cột `published`, nhằm mô phỏng lỗi mất các paper mới nhất.
5. Blank summary trên một nhóm record để mô phỏng lỗi thiếu nội dung.
6. Inject destructive noise vào summary, không chỉ append chuỗi vô nghĩa, mà thay một phần nội dung bằng noise để có khả năng ảnh hưởng semantic embedding.
7. Truncate/damage title để làm giảm chất lượng thông tin tiêu đề.
8. Make publication dates stale bằng cách trừ nhiều năm khỏi `published`, sau đó tính lại `age_days`.
9. Add duplicate rows để tạo lỗi duplicate `paper_id`.
10. Rebuild helper fields gồm `summary_chars`, `age_days`, `text_for_embedding` để downstream modules nhìn thấy đúng dữ liệu sau corruption.
11. Write audit log vào JSON để truy vết record nào bị ảnh hưởng bởi loại corruption nào.
12. Mock self-test bằng `__main__` để có thể kiểm tra nhanh module độc lập với toàn bộ pipeline.

## 6. Input, output và contract

| Thành phần              | Mô tả                                                                                                        |
| ----------------------- | ------------------------------------------------------------------------------------------------------------ |
| Input                   | Clean dataframe từ baseline pipeline                                                                         |
| Required columns        | `paper_id`, `title`, `summary`, `published`                                                                  |
| Optional/helper columns | `authors_joined`, `categories_joined`, `primary_category`, `age_days`, `summary_chars`, `text_for_embedding` |
| Output                  | Corrupted dataframe có cùng schema chính và đã rebuild helper fields                                         |
| Artifact                | `data/results/corruption_log.json` hoặc mock log khi chạy self-test                                          |
| Module phụ thuộc        | `src/ingestion/cleaning.py` tạo clean dataframe                                                              |
| Module sử dụng output   | `src/pipelines/corruption_flow.py`, embedding/index builder, evaluation, quality checks                      |
| Điều kiện lỗi cần xử lý | Empty dataframe, thiếu required columns, fraction ngoài khoảng 0–1, non-overlap group vượt quá số dòng       |

## 7. Cách xác minh

```bash
python src/ingestion/corruption.py
```

Kết quả mong đợi:

```text
Running corruption.py mock tests...
PASS: basic corruption test
PASS: reproducibility test
PASS: zero-fraction test
PASS: missing required columns test
PASS: empty dataframe test

All mock tests passed.
```

Artifact/log cần kiểm tra:

```text
data/results/mock_corruption_log.json
data/results/mock_corruption_log_first.json
data/results/mock_corruption_log_second.json
data/results/mock_corruption_log_zero.json
```

## 8. Một quyết định kỹ thuật quan trọng

* **Bối cảnh:** Corruption có thể được tạo ngẫu nhiên hoàn toàn, nhưng nếu quá ngẫu nhiên thì metrics khó tái lập và khó giải thích nguyên nhân.
* **Các phương án đã cân nhắc:**

  1. Random corruption không seed, mỗi lần chạy tạo lỗi khác nhau.
  2. Controlled corruption có seed, log theo `paper_id`, không mutate baseline.
* **Phương án đã chọn:** Controlled corruption có seed và audit log.
* **Lý do:** Cách này tốt hơn cho data observability vì có thể reproduce, so sánh baseline/corrupted/repaired công bằng, và truy vết chính xác record bị ảnh hưởng.
* **Bằng chứng quyết định phù hợp:** Mock test `reproducibility` có thể chạy hai lần với cùng seed và so sánh hai corrupted dataframe bằng `pd.testing.assert_frame_equal()`.

## 9. Một lỗi hoặc blocker đã xử lý

* **Triệu chứng/lỗi:** Nếu dùng fraction bằng `0`, hàm vẫn có thể corrupt ít nhất một dòng do logic `max(1, round(...))`.
* **Lệnh hoặc bước tái hiện:** Gọi `corrupt_clean_dataframe()` với toàn bộ corruption fractions bằng `0`.
* **Nguyên nhân gốc:** Hàm convert fraction sang count không phân biệt `fraction=0` với `fraction>0`.
* **Cách xử lý:** Tạo helper `_fraction_to_count()`, trong đó `fraction <= 0` trả về `0`, còn `fraction > 0` mới đảm bảo ít nhất một dòng nếu dataframe không rỗng.
* **Cách xác minh sau khi sửa:** Self-test `_test_zero_fraction_no_change_except_rebuild()` kiểm tra row count, `paper_id`, `title`, `summary`, `published` không bị thay đổi.
* **Điều học được:** Với data experiment, các edge cases nhỏ như zero fraction rất quan trọng vì chúng ảnh hưởng đến khả năng kiểm soát và tái lập của pipeline.

## 10. Hiểu biết về luồng end-to-end

### Dữ liệu đi từ Crossref đến vector index như thế nào?

Dữ liệu được lấy từ Crossref API, parse thành các raw records theo schema thống nhất, lưu snapshot vào `data/raw/`, sau đó cleaning pipeline chuẩn hóa title, summary, author, category, date và tạo `text_for_embedding`. Từ cleaned data, embedding module tạo vector và nạp vào ChromaDB để agent có thể retrieval context khi trả lời câu hỏi.

### Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?

Evaluation set chứa các câu hỏi, câu trả lời đúng và `ground_truth_doc_ids`. Khi agent truy vấn vector index, retrieval được xem là tốt nếu top-k context chứa đúng document ID cần thiết. Answer quality được đo bằng các metric như token F1 hoặc judge score dựa trên câu trả lời của agent so với ground truth.

### Quality checks khác freshness monitoring ở điểm nào?

Quality checks tập trung vào tính hợp lệ của dữ liệu như row count, `paper_id` unique, title không rỗng, summary đủ dài, duplicate hoặc missing fields. Freshness monitoring tập trung vào độ mới của dữ liệu, ví dụ record có quá cũ so với `freshness_threshold_days` hay không.

### Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?

Nếu mỗi trạng thái dùng một test set khác nhau thì metrics không còn so sánh công bằng. Dùng cùng `test_set.json` giúp chứng minh thay đổi metrics đến từ chất lượng dữ liệu, không phải do câu hỏi đánh giá thay đổi.

### Repair được xem là thành công dựa trên artifact và metric nào?

Repair được xem là thành công khi repaired dataset được rebuild từ raw records, quality/freshness checks phục hồi, và metrics của repaired state tiến gần baseline hơn corrupted state. Các artifact cần đối chiếu gồm `repaired_clean.csv/json`, `repaired_metrics.json`, `repaired_answers.json` và comparison report.

## 11. Phân tích kết quả

Các giá trị dưới đây cần được điền sau khi chạy end-to-end pipeline trên môi trường local hoặc nhóm:

| Metric/signal        |  Baseline | Corrupted |  Repaired | Nhận xét cá nhân                                              |
| -------------------- | --------: | --------: | --------: | ------------------------------------------------------------- |
| `retrieval_hit_rate` | Chưa chạy | Chưa chạy | Chưa chạy | Kỳ vọng corrupted giảm và repaired phục hồi gần baseline      |
| `mean_token_f1`      | Chưa chạy | Chưa chạy | Chưa chạy | Kỳ vọng answer quality giảm khi summary/title bị phá semantic |
| `judge_accuracy`     | Chưa chạy | Chưa chạy | Chưa chạy | Có thể dao động nếu dùng LLM judge                            |
| `mean_judge_score`   | Chưa chạy | Chưa chạy | Chưa chạy | Nên so sánh xu hướng thay vì chỉ nhìn một điểm                |
| Quality checks       | Chưa chạy | Chưa chạy | Chưa chạy | Kỳ vọng corrupted fail duplicate/blank/stale checks           |
| Freshness status     | Chưa chạy | Chưa chạy | Chưa chạy | Kỳ vọng stale date làm freshness degraded                     |

### Kết luận từ số liệu dự kiến

Data corruption như blank summary, noisy summary, dropped latest records và duplicate rows sẽ làm quality/freshness signals xấu đi, đồng thời có khả năng làm retrieval hoặc answer metrics giảm.

Repair từ raw records sẽ phục hồi cleaned dataset, rebuild index và giúp metrics tăng trở lại so với corrupted state.

Corruption có khả năng ảnh hưởng rõ nhất là **drop latest records** và **blank/noisy summary**, vì chúng trực tiếp làm mất hoặc phá nội dung được embed. Duplicate rows và stale date thường dễ bị observability phát hiện, nhưng có thể không làm RAG metric giảm mạnh nếu câu hỏi evaluation không phụ thuộc vào các record đó.

## 12. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Data pipeline không chỉ cần chạy được, mà cần có artifact để truy vết từng giai đoạn: raw, clean, embedding, metrics và reports.
2. Data observability cần kiểm tra cả lỗi schema/content và lỗi freshness, vì mỗi loại lỗi ảnh hưởng pipeline theo một cách khác nhau.
3. Với RAG agent, chất lượng retrieval phụ thuộc trực tiếp vào chất lượng `text_for_embedding`; nếu text bị thiếu hoặc nhiễu thì agent có thể trả lời sai dù model vẫn hoạt động bình thường.

### Nếu có thêm thời gian

Tôi muốn bổ sung corruption có mục tiêu dựa trên `ground_truth_doc_ids` trong evaluation set. Khi đó một phần record được chọn để corrupt sẽ chắc chắn liên quan đến câu hỏi đánh giá, giúp comparison giữa baseline, corrupted và repaired rõ hơn thay vì phụ thuộc hoàn toàn vào random sampling.

## 13. Cam kết của thành viên

* [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
* [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
* [x] Mọi kết luận về kết quả đều được ghi rõ là đã có artifact hoặc cần chạy pipeline để xác minh.
* [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
* [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
* [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** TRẦN ANH VĂN
**MSSV:** 2A202601513
**Ngày xác nhận:** 2026-08-06
