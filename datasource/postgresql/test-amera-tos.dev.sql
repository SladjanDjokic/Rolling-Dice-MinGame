INSERT INTO amera_tos ( status, contract_text, in_service_date, suspend_date ) VALUES 

  ( 'active', 'Lorem ipsum dolor sit amet, consectetur adipiscing elit. In vulputate, eros sit amet imperdiet luctus, quam lorem eleifend lorem, non pretium leo enim et ante. Pellentesque facilisis tristique lorem sed maximus. Phasellus tincidunt rutrum est, non ullamcorper nisl mattis at. Donec at erat purus. Nulla tincidunt viverra volutpat. Mauris egestas neque ut ex condimentum, vitae pharetra nibh malesuada. Cras ac facilisis nunc, non maximus quam. Sed porttitor magna sed dolor pellentesque faucibus. Sed semper ac neque in pharetra. In iaculis, metus quis pellentesque ultrices, erat dui mollis dui, hendrerit pharetra massa nulla at ex. Vestibulum ac molestie massa, id sodales eros. Vestibulum eu metus condimentum, viverra arcu non, vehicula quam.
Fusce id sagittis arcu. Orci varius natoque penatibus et magnis dis parturient montes, nascetur ridiculus mus. Aenean velit dui, dictum ac pulvinar et, auctor at metus. Integer ornare volutpat nibh, nec consectetur ante sagittis ac. Nullam nunc tortor, ornare auctor pretium at, venenatis sit amet nisi. Ut tempus commodo velit. Morbi vestibulum tristique justo ac laoreet. Donec vitae nisi vehicula, sagittis eros eget, posuere elit. Maecenas nulla eros, tincidunt nec justo in, maximus facilisis ligula. Donec molestie dolor vel feugiat rutrum. Vivamus eu congue urna.', CURRENT_DATE, CURRENT_DATE ),
  ( 'inactive', 'Inactive contract text', CURRENT_DATE, CURRENT_DATE ),
  ( 'deleted', 'Deleted contract text', CURRENT_DATE, CURRENT_DATE ),
  ( 'active', 'Parle france', CURRENT_DATE, CURRENT_DATE ),
  ( 'active', 'I speak Russian', CURRENT_DATE, CURRENT_DATE ),
  ( 'active', 'I speak JP', CURRENT_DATE, CURRENT_DATE );


-- 
INSERT INTO amera_tos_country ( amera_tos_id, country_code_id ) VALUES
  -- Active for US
  ( 1, 840 ),
  -- Inactive for US
  ( 2, 840 ), 
  -- Deleted for US
  ( 3, 840 ),
  -- Active for France
  ( 4, 250 ),
  -- Active for Russian
  ( 5, 643 ),
  -- Active for JP
  ( 5, 392 );