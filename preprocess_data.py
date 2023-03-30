# This file should prepare the data by splitting it into first and second halfs, removing noise, and shortening it
# down to a manageable size for efficiency.

from xml.dom import minidom as mdom
import pandas as pd


def get_attr_value(ele, attr):
    return ele.attributes[attr].value


def split_halves(metadata_filename):
    """
    extracts metadata of game from a provided file and returns the details in a dictionary
    :param metadata_filename: the metadata file given with the game data
    :return: 3 dictionaries: pitch, which is the size details of the game pitch; first_half and second half,
    which gives the frames of the start and end of the first and second half, respectively
    """
    metadata = mdom.parse(metadata_filename)

    # Finding the size of the pitch
    match = metadata.getElementsByTagName('match')[0]
    tracking_size = {'x': float(get_attr_value(match, 'fTrackingAreaXSizeMeters')),
                     'y': float(get_attr_value(match, 'fTrackingAreaYSizeMeters'))}

    pitch = {'x': float(get_attr_value(match, 'fPitchXSizeMeters')),
             'y': float(get_attr_value(match, 'fPitchYSizeMeters'))}

    # finding the beginning and end frames of the first + second half
    first = metadata.getElementsByTagName('period')[0]
    second = metadata.getElementsByTagName('period')[1]

    first_half = {'start': int(get_attr_value(first, 'iStartFrame')), 'end': int(get_attr_value(first, 'iEndFrame'))}
    second_half = {'start': int(get_attr_value(second, 'iStartFrame')), 'end': int(get_attr_value(second, 'iEndFrame'))}

    return [pitch, tracking_size, first_half, second_half]


pitch, tracking_size, first_half, second_half = split_halves('data/metadata/metadata.xml')


def eliminate_noise(half1, half2, datafile):
    """
    Produces a new .dat file with only active play (i.e. play during the first and second half)
    :param half1: extracted metadata about the first half
    :param half2: extracted metadata about the second half
    :param datafile: .dat file to be cleaned
    :return: name of the new file produced
    """
    half1_start = half1['start']
    half1_end = half1['end']
    half2_start = half2['start']
    half2_end = half2['end']

    with open(datafile, "r") as input_file:
        with open("data/gamedata/in_play.dat", "w") as output_file:
            start_processing = False
            for line in input_file:
                # get the frame number and cast to an int to compare
                frame = int(line.strip().split(":")[0])

                # print(frame, start_processing)
                if not start_processing:
                    # check if the target column has the target value
                    if frame == half1_start or \
                            frame == half2_start:
                        start_processing = True
                        output_file.write(line)
                # check if the frame is an end frame and stop processing if so
                elif frame == half1_end or \
                        frame == half2_end:
                    start_processing = False
                else:
                    # write the line to the new file
                    output_file.write(line)

    return output_file.name


def shorten_data(seconds, filename):
    """
    produces a new data file which only contains every x seconds the user specifies
    :param seconds: seconds per data capture. NB: this parameter refers to real seconds, NOT frames
    :param filename: name of the file to shorten down
    :return: the name of the new file produced
    """
    # 25 frames per second:
    n = seconds * 25

    with open(filename, "r") as file:
        with open("data/gamedata/short_data.dat", "w") as newfile:
            shortened_data = []
            for i, line in enumerate(file):
                if i % n == 0:
                    newfile.write(line)

    return newfile.name


# calculating amount to cut off tracking boundaries
excess_x = ((tracking_size['x'] - pitch['x']) / 2) * 100
excess_y = ((tracking_size['y'] - pitch['y']) / 2) * 100

max_x = (tracking_size['x'] * 50) - excess_x
max_y = (tracking_size['y'] * 50) - excess_y


def scale_data_to_pitch(orig_x, orig_y):
    # calculating the pitch borders in tracking terms

    x = (int(orig_x) + max_x) / 100
    y = (int(orig_y) + max_y) / 100

    #print(f"OLD X: {orig_x}\n NEW: {x}")
    #print(f"OLD Y: {orig_y}\n NEW: {y}")

    return x, y


def categorize_data(filename):
    """
    splits the data into two CSV files: players and ball
    :param filename: the name of the file to categorize
    :return: void
    """

    player_data = []
    ball_data = []

    with open(filename, 'r') as file:
        for i in file:
            # create frame num, list of players, and ball details
            frame_num = i.split(':')[0]
            players = i.split(':')[1].split(';')
            ball = i.split(':')[2].split(',')

            # if (min_max_x[0] < int(ball[0]) < min_max_x[1]) and (min_max_y[0] < int(ball[1]) < min_max_y[1]):
            # add frame details to ball data and add to list
            ball[0], ball[1] = scale_data_to_pitch(ball[0], ball[1])

            if (0 < int(ball[0]) < pitch['x']) and (0 < int(ball[1]) < pitch['y']):
                ball_frame = [frame_num, ball[0], ball[1], ball[2], ball[3], ball[4], ball[5].strip(';')]
                ball_data.append(ball_frame)

            # add frame details to each player and add them to list
            for j in players:
                data = j.split(',')

                # getting rid of any data outside borders of the pitch
                # converting tracking data to meters
                if len(data) > 1:
                    # convert x and y to positive values and reduce scale to metres
                    data[3], data[4] = scale_data_to_pitch(data[3], data[4])

                    if (0 < int(data[3]) < pitch['x']) and (0 < int(data[4]) < pitch['y']):
                        # remove any frames that are outside the pitch borders
                        # if data[3] <= pitch['x'] and data[4] <= pitch['y']:
                        player_frame = [frame_num, data[0], data[1], data[2], data[3], data[4], data[5]]
                        player_data.append(player_frame)

    # add ball to CSV
    ball_df = pd.DataFrame(ball_data, columns=['frame_num', 'x', 'y', 'z', 'speed', 'poss', 'inPlay'])
    ball_df.to_csv('./data/ball.csv/ball_df.csv')

    # add players to CSV
    player_df = pd.DataFrame(player_data, columns=['frame_num', 'team_id', 'player_id', 'squadNum', 'x', 'y', 'speed'])
    player_df.to_csv('./data/player.csv/player_df.csv')


# clean up file
categorize_data(shorten_data(1, eliminate_noise(first_half, second_half, 'data/gamedata/987601.dat')))
