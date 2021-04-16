-- ------------------------------------------------------------------------------
-- Table:        stream_media_type
-- Description:  type pull down on stream page
-- ------------------------------------------------------------------------------

INSERT INTO stream_media_type (name)

  VALUES    ( 'Amera Promotional Videos' ),
            ( 'Branding Videos' ),
            ( 'Company Profile Videos' ),
            ( 'Conference Videos' ),
            ( 'Executive Messaging' ),
            ( 'Industrial Videos' ),
            ( 'Internal Communication Videos' ),
            ( 'Promotional Videos' ),
            ( 'Recruitment Videos' ),
            ( 'Social Media Videos' ),
            ( 'Social Responsibility Videos' ),
            ( 'Testimonial Videos' ),
            ( 'Training Videos' );

-- ------------------------------------------------------------------------------
-- Table:        stream_media_category
-- Description:  category row on stream page
-- ------------------------------------------------------------------------------

INSERT INTO stream_media_category (name)

  VALUES    ( 'Streaming Now' ),
            ( 'Upcoming Streams' ),
            ( 'Past Streams' );
            