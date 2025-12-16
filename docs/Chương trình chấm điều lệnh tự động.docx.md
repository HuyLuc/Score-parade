Chương trình Chấm Điều Lệnh là chương trình nhận đầu vào là video hình ảnh chiến sĩ/sĩ quan thực hành đi theo điều lệnh.   
Người dùng phần mềm sẽ phải đăng ký tài khoản (RegisterView). Nếu đã có tài khoản rồi thì đăng nhập (LoginView). 

Khi đăng nhập xong thì người đó có thể thêm danh sách thí sinh (ListOfCandidatesView). Thêm danh sách đó có thể nạp dữ liệu từ file Excel hoặc thêm thủ công từng người. Thêm thủ công từng người thì sẽ có CreateCandidateView 

Sau đó thì người dùng có thể vào màn hình cấu hình (ConfigurationView) để thực hiện các chức năng: (i) đổi mật khẩu, (ii) chọn chế độ kiểm tra hay luyện tập; (iii) chọn tiêu chí đi đều hay đi nghiêm; (iv) chọn mức độ khắt khe khi chấm; (v) chọn chế độ hoạt động là dev hay release. 

Người dùng có thể vào màn hình Barem (BaremView) để xem lại các tiêu chí chấm điểm, và điểm trừ nếu người thí sinh mắc lỗi ở tiêu chí đó.

Sau đó người dùng vào màn hình ObservationView:  
Màn hình sẽ hiển thị hình ảnh của HAI camera. Người dùng nếu thấy đúng là người mình đang muốn chấm (có trong danh sách thí sinh) thì người dùng sẽ cho phát nhạc  
Bất kỳ file nhạc nào được phát ra thì trước đó có câu sau được phát: Nghiêm. Đi đều bước”  
Với chế độ nào cũng phải trả qua bài chấm “Làm chậm”. Chấm “Làm chậm” là chỉ xét tay, chân, vai, mũi, cổ, lưng có đúng tư thế hay không? “Làm chậm” nếu ở chế độ kiểm tra thì phải trừ dần điểm (điểm ban đầu là 100\) đến Mnf hình50 là báo trượt, kết thúc kiểm tra. “Làm chậm” nếu ở chế độ luyện tập thì chỉ hiển thị các thông báo về lỗi sai và thông báo này xuất hiện theo kiểu Stack    
Sau khi kết thúc bài chấm “Làm chậm” thì trải qua bài chấm “Tổng hợp”. Chấm “tổng hợp” là có xét đến việc: (i) các động tác của cơ thể có theo đúng nhịp của bài nhạc hay không? (ii) các bước chân và việc vung tay có quá dài/quá cao/quá xa so với quy định hay không (iii) tốc độ thực hiện các động tác có quá nhanh hay quá chậm không?   
Sau khi chấm xong bài “Tổng hợp” thì người dùng sẽ được nhìn thấy màn hình Kết thúc phiên chấm (EndOfSectionView). Trong màn hình này sẽ có danh sách các lỗi, chi tiết lỗi, điểm trừ (nếu ở chế độ Kiểm tra) và nút nhấn xem của từng lỗi (nhấn vào sẽ xem được hình ảnh của lỗi  \- nếu lỗi xuất hiện khi làm chậm \- hoặc xem được video chỗ xảy ra lỗi \- nếu lỗi xuất hiện khi “tổng hợp”)

Về nhạc thì nhạc đi đều và nhạc đi nghiêm khác nhau ở nội dung. **Nhạc đi đều ở chế độ kiểm tra làm chậm và nhạc đi đều ở chế độ luyện tập làm chậm thì chỉ khác nhau về thời lượng**. **Nhạc đi nghiêm ở chế độ kiểm tra làm chậm và nhạc đi nghiêm ở chế độ luyện tập làm chậm thì chỉ khác nhau về thời lượng**. **Nhạc đi đều tổng hợp cũng sẽ khác các file nhạc đi đều khác ở thời lượng** 

Người dùng khi chấm hết tất cả các thí sinh sẽ xem được màn tổng hợp (SummaryView). Trong màn hình này sẽ hiển thị ra tất cả các thí sinh đã được chấm, STT, thời điểm chấm, điểm chấm, …

Dự kiến danh sách các lớp thuộc nhóm Model:  
Person (đại diện cho người chung, có name, password, token, gender, rank (cấp bậc \- chẳng hạn đại đội trưởng), insignia (quân hàm \- chẳng hạn đại uý).

Soldier (chiến sĩ)  
Officer (sĩ quan)

PartOfBody (đại diện cho bộ phận của cơ thể, có thuộc tính name, position). Lớp này có các lớp con là Nose, Neck, Shoulder, Arm, Elbow (khuỷu), Fist (nắm tay), Hand, Back, Knee, Foot

Có lớp Score đại diện cho điểm (có thuộc tính value, createdAt \- thời điểm tạo, listOfModifiedTimes \- các lần trừ điểm và bị trừ bao nhiêu điểm)

Có lớp Criterion đại diện cho tiêu chí chấm (có thuộc tính id, content, action \- là một lambda function, weight \- trọng số)

Có lớp Audio, Video và Log 

Dự kiến danh sách các lớp thuộc nhóm View:  
RegisterView, LoginView, ConfigurationView, BaremView, ObservationView, ListOfCandidatesView, EndOfSectionView, SummaryView

Sẽ có các lớp đại diện cho Controller như sau:  
RegisterController, LoginController, ConfigurationController, CandidateController, BaremController, DifficultController, LogController, 

CandidateController (điều khiển việc chọn thí sinh), CameraController (điều khiển việc kết nối và nhận dữ liệu từ Camera), ModeController (chế độ hoạt động là làm chậm hay tổng hợp), LocalController (điều khiển việc chấm theo chế độ làm chậm kiểm tra \- LocalTestingController hoặc chế độ làm chậm luyện tập \- LocalPractisingController), GlobalController (điều khiển việc chấm theo chế độ tổng hợp kiểm tra \- GlobalTestingController, hoặc chế độ tổng hợp luyện tập \- GlobalPractisingController). 

SnapshotController (điều khiển việc trích xuất ảnh từ dữ liệu video streaming do Camera trả về), VideoController (điều khiển việc cắt lấy video từ dữ liệu video streamming do Camera trả về).

EndOfSectionController (điều khiển việc hiển thị thống kê khi thí sinh vừa được chấm xong)

SummaryController (điều khiển việc hiển thị thống kê khi chấm xong tất cả các thí sinh)

	DBController (điều khiển việc truy xuất CSDL trong máy)

	AIController để phát hiện lỗi của người thí sinh 

Mô tả luồng hoạt động:  
1\) Luồng đăng ký:  
Actor mở RegisterView, nhập vào họ và tên, username (tên đăng nhập), mật khẩu, tuổi, cấp bậc, quân hàm, avatar (nếu có)  
	Actor nhấn vào nút Submit hoặc nút Erase của RegisterView  
		Nếu nhấn nút Submit thì:  
Kích hoạt RegisterController và RegisterController sẽ gọi hàm validate dữ liệu   
Nếu validate thành công sẽ gọi đến DBController. DBController sẽ kiểm tra xem tài khoản này có bị trùng hay không? Nếu không trùng thì sẽ tạo tài khoản trong CSDL  
Tạo thành công thì RegisterView sẽ hiển thị thông báo chúc mừng tạo tài khoản thành công  
		Nếu nhấn nút Erase thì xoá toàn bộ dữ liệu trên form của RegisterView

2\) Luồng đăng nhập  
	Actor mở LoginView, nhập vào tên, mật khẩu  
	Actor nhấn vào nút Login  
		Kích hoạt LoginController để nó gọi hàm validate dữ liệu  
Nếu validate thành công sẽ gọi đến DBController và nó sẽ kiểm tra xem username và mật khẩu có đúng không?   
Nếu đúng thì cấp cho token và chuyển sang màn hình tiếp theo ListOfCandidatesView  
Nếu sai thì sẽ báo người dùng nhập sai username hoặc mật khẩu  
Nếu validate không thành công thì báo người dùng nhập sai username hoặc mật khẩu

3\) Luồng chọn thí sinh  
	Actor mở ListOfCandidatesView:  
Actor sẽ chọn lựa thí sinh từ trong danh sách. Nếu chưa chọn thì nút “Next” sẽ bị mờ (không nhấn được)  
		Nếu nhấn nút Next thì sẽ chuyển sang màn hình ObservationView  
		Nếu nhấn nút Configure thì sẽ chuyển sang màn hình ConfigurationView  
Nếu nhấn nút Import sẽ chuyển sang tuỳ chọn Import danh sách hay CreateCandidateView để tạo thí sinh mới   
	Nếu Import danh sách thì sẽ chọn file Excel để nạp vào  
Khi chọn xong file thì sẽ hiển thị CandidateController. Đối tượng của lớp này sẽ kiểm tra dữ liệu (validate) để xem có sai sót gì không? Nếu không có sai sót gì thì sẽ gọi DBController để chèn dữ liệu vào  
Thí sinh đầu tiên trong danh sách được thêm mới đó sẽ là thì sinh được chọn   
Nếu Create thí sinh mới sẽ hiển thị form CreateCandidateView (khá giống với form RegisterView)  
Khi người dùng nhập xong dữ liệu thì CandidateController sẽ kiểm tra dữ liệu. Nếu không có sai sót gì thì DBController sẽ được gọi để chèn dữ liệu vào  
Thí sinh mới được tạo sẽ là thí sinh được chọn.   
Ở đây nếu nhấn Cancel thì sẽ đóng màn hình và chuyển về màn hình ListOfCandidatesView. Còn nếu nhấn Next sẽ chuyển sang ObservationView (cho thí sinh đầu tiên trong danh sách hoặc thí sinh vừa được tạo mới)  
		Actor có thể sửa/xóa một thí sinh

4\) Luồng chỉnh Barem:  
	Actor mở BaremView:  
		Nếu nhấn nút Barem sẽ chuyển sang màn hình BaremView  
BaremController sẽ kết nối với DBController để lấy dữ liệu và hiển thị trên BaremView. Một loạt các đối tượng của Criterion sẽ được tạo  
Người dùng sẽ có thể điều chỉnh trọng số điểm của các lỗi rồi nhấn nút Submit  
BaremController sẽ validate dữ liệu. Nếu validate thành công sẽ yêu cầu DBController cập nhật lại. DBController sẽ cập nhật dữ liệu nếu validate cũng thành công. Nếu cập nhật thành công thì đối tượng của Criterion tương ứng sẽ được cập nhật  
Ở đây nếu nhấn Cancel thì sẽ đóng màn hình và chuyển về màn hình ListOfCandidatesView. Còn nếu nhấn Next và đã có thí sinh được chọn  thì sẽ chuyển sang ObservationView. Còn nếu chưa có thí sinh được chọn thì sẽ chuyển về màn hình ListOfCandidatesView  
5\) Luồng cấu hình:  
	Actor mở ConfigurationView:  
Nếu tích chọn chế độ tổng hợp hoặc làm chậm thì đối tượng của ModeController sẽ được khởi tạo là LocalController hay GlobalController  
Nếu tích chọn bài chấm là kiểm tra hay luyện tập thì đối tượng của ModeController sẽ được khởi tạo là LocalTestingController hay LocalPractisingController.  
Nếu chọn độ khắt khe thì sẽ tuỳ chọn thông số (bằng cách gọi hàm adjust) của lớp DifficultController  
Nếu chọn chế độ hoạt động là Dev hay Release thì tương ứng đối tượng của lớp DevController và ReleaseController (là lớp con của LogController) sẽ được tạo  
Nếu chọn tiêu chí chấm là đi đều hay đi nghiêm thì một thuộc tính của ObserverController sẽ được cập nhật  
Nếu chọn Next (và đã có thí sinh được chọn) thì chương trình sẽ chuyển sang ObservationView   
Nếu nhấn Back thì chương trình sẽ quay lại màn hình ListOfCandidatesView

6\) Luồng chấm một thí sinh:  
	Actor mở ObservationView:  
Chương trình sẽ hiển thị popup trong đó ghi rõ: tiêu chí chấm là đi đều hay đi nghiêm, chế độ kiểm tra hay luyện tập, thông tin của thí sinh được chấm   
CameraController sẽ được kích hoạt, gọi đến các hàm cần thiết để kết nối với HAI Camera và hiển thị được hình ảnh từ HAI camera  
Nếu không kết nối được thì CameraController sẽ phải cố kết nối lại hoặc sẽ hiển thị thông báo để người dùng kiểm tra lại camera (hoặc đường kết nối)		  
Người dùng sẽ chọn lựa thí sinh từ danh sách (nếu người được chấm không đúng theo thứ tự). Tức CandidateController sẽ được gọi đến các hàm của nó  
CandidateController sẽ hiển thị 1 giao diện (gần giống với ListOfCandidatesView) để người dùng chọn lấy thí sinh phù hợp  
		Người dùng chọn xong thí sinh thì sẽ nhấn nút OK hoặc Cancel  
			Nếu nhấn Cancel thì sẽ chuyển sang lại trang ListOfCandidateView   
			Nếu nhấn OK thì chương trình sẽ phát nhạc  
Nếu chế độ kiểm tra thì điểm ban đầu sẽ là 100 và trừ dần nếu người dùng làm sai. Ngoài ra lỗi mắc phải sẽ được hiển thị  
Nếu chế độ luyện tập thì chỉ hiển thị lỗi mắc phải thôi  
Tuỳ vào đối tượng của ModeController (LocalTestingController hay LocalPractisingController) mà đối tượng đó sẽ gọi đến SnapshotController theo chu kỳ để lấy ra ảnh  
Đối tượng của ModeController lấy được ảnh thì sẽ gọi đến AIController và AIController sẽ sử dụng cả DifficultController để phát hiện lỗi  
Với lỗi được phát hiện thì đối tượng của ModeController sẽ kích hoạt ObservationView để hiển thị (trừ điểm hay hiển thị lỗi). SnapshotController sẽ lưu ảnh của lỗi  
Nếu điểm mà bị trừ xuống còn dưới 50 thì tự động chuyển sang màn EndOfSectionView. ModeController và SnapshotController sẽ truyền dữ liệu cho EndOfSectionController  
Sau khi chấm xong phần làm chậm thì đối tượng của ModeController tự tạo ra một đối tượng của GlobalTestingController hay GlobalPractisingController  
			Chương trình sẽ phát nhạc  
Nếu chế độ kiểm tra thì điểm sẽ dùng lại điểm của lần làm chậm và trừ dần nếu người dùng làm sai. Ngoài ra lỗi mắc phải sẽ được hiển thị  
Nếu chế độ luyện tập thì chỉ hiển thị lỗi mắc phải thôi  
Tuỳ vào đối tượng của ModeController (GlobalTestingController hay GlobalPractisingController) mà đối tượng đó sẽ gọi đến VideoController theo chu kỳ để lấy ra ảnh frame của video   
Đối tượng của ModeController lấy được ảnh thì sẽ gọi đến AIController và AIController sẽ sử dụng cả DifficultController để phát hiện lỗi  
Với lỗi được phát hiện thì đối tượng của ModeController sẽ kích hoạt ObservationView để hiển thị (trừ điểm hay hiển thị lỗi). VideoController sẽ lưu đoạn video có chứa lỗi  
Nếu điểm mà bị trừ xuống còn dưới 50 thì tự động chuyển sang màn EndOfSectionView. ModeController và VideoController sẽ truyền dữ liệu cho EndOfSectionController  
Sau khi chấm xong phần tổng hợp thì đối tượng của ModeController sẽ chuyển sang màn EndOfSectionView  
	  
7\) Luồng xem điểm của một thí sinh:  
Actor mở EndOfSectionView:  
Khi đó EndOfSectionController sẽ hiển thị dữ liệu lên EndOfSectionView (chia thành các tab với từng loại lỗi (lỗi làm chậm, lỗi tổng hợp nhịp, lỗi tổng hợp khoảng cách, lỗi tổng hợp tốc độ)  
Actor có thể nhấn Next để hiển thị màn ListOfCandidatesView (với thí sinh được chọn có thể là người tiếp theo trong danh sách hoặc người còn lại)  
Actor có thể nhấn Finish để chuyển sang màn SummaryView để xem tổng kết chấm tất cả thí sinh từ trước đến nay  
EndOfSectionController sẽ truyền dữ liệu cho SummaryController  
Actor có thể xóa một kết quả thi của một thí sinh

8\) Luồng xem tổng kết:  
	Actor mở SummaryView:  
		SummaryController sẽ sử dụng dữ liệu được lấy từ EndOfSectionController  
Ngoài ra SummaryController sẽ gọi đến DBController để hiển thị các phiên chấm trước đó.   
Actor có thể xóa một số kết quả thi của một số thí sinh  
Actor có thể nhấn Resume để bắt đầu việc chấm tiếp (chuyển sang ListOfCandidatesView)  
	Actor có thể nhấn Finish để kết thúc việc chấm, phần mềm sẽ thoát

	