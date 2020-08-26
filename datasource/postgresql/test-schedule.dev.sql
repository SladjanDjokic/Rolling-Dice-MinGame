INSERT INTO member_scheduler_setting 
        (member_id, date_format, time_format, start_time, time_interval, start_day)
        VALUES 
        (1, 'MM/DD/YYYY', '24Hr', 5, 1, 3),
        (4, 'YY/MM/DD', 'AM/PM', 8, 2, 1);


INSERT INTO file_storage_engine (storage_engine_id,storage_engine,status,create_date,update_date) VALUES 
('https://file-testing.s3.us-east-2.amazonaws.com/1597718891765-Screenshot from 2020-08-09 09-57-00.png','S3','available','2020-08-17 21:48:11.750','2020-08-17 21:48:11.750')
,('https://file-testing.s3.us-east-2.amazonaws.com/1597718910795-Screenshot from 2020-08-09 09-57-00.png','S3','available','2020-08-17 21:48:20.480','2020-08-17 21:48:20.480')
;

INSERT INTO member_file (file_id,file_name,status,member_id,categories,file_ivalue) VALUES 
(1,'Screenshot from 2020-08-09 09-57-00.png','available',2,'EventImage',NULL)
,(2,'Screenshot from 2020-08-09 09-57-00.png','available',3,'EventImage',NULL)
;

INSERT INTO schedule_event 
        (event_name,event_host_member_id,event_type,event_datetime_start,event_datetime_end,event_location_address,event_location_postal,event_recurrence,event_image,create_date,update_date) 
        VALUES 
        ('test event1',1,'Video','2020-07-16 15:31:00.000','2020-07-16 17:31:00.000','event test address1','','Weekly',1,'2020-08-17 20:49:25.331','2020-08-17 20:49:25.331')
        ,('test event2',1,'Audio','2020-08-16 15:31:00.000','2020-08-16 17:31:00.000','event test address2','','Weekly',2,'2020-08-17 20:49:39.439','2020-08-17 20:49:39.439')
        ,('test event3',2,'Chat','2020-09-16 15:31:00.000','2020-09-17 17:31:00.000','event test address3','','Monthly',2,'2020-08-17 20:49:55.593','2020-08-17 20:49:55.593')
        ,('test event4',3,'Audio','2020-07-16 15:31:00.000','2020-07-16 17:31:00.000','event test address4','','Weekly',1,'2020-08-17 20:50:15.848','2020-08-17 20:50:15.848')
        ,('test event5',1,'Video','2020-10-16 15:31:00.000','2020-10-16 17:31:00.000','event test address5','','Monthly',1,'2020-08-17 20:50:31.398','2020-08-17 20:50:31.398')
        ,('test event6',4,'Chat','2020-09-16 15:31:00.000','2020-09-17 17:31:00.000','event test address6','','Weekly',2,'2020-08-17 20:50:48.426','2020-08-17 20:50:48.426')
        ,('test event7',4,'Video','2020-08-16 15:31:00.000','2020-08-16 17:31:00.000','event test address7','','Yearly',1,'2020-08-17 20:51:03.839','2020-08-17 20:51:03.839');