#!/usr/bin/env python

'''
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!   NOTE: SCRIPT NEEDS TO BE COMPATIBLE WITH PYPY3!
!   THIS SAMPLE IS BUILT USING MIMESIS 11.1.0.
!   IF YOU ARE USING A SCRIPT THAT USES AN OLDER VERSION,
!   YOU NEED TO EITHER UPGRADE YOUR CODE TO MATCH THIS TEMPLATE
!   OR GO INTO THE REQUIREMENTS FILE AND CHANGE THE MIMESIS VERSION
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
'''

########################################################################
# 
# This is an example Locust file that use Mimesis to help generate
# dynamic documents. Mimesis is more performant than Faker
# and is the recommended solution. After you build out your tasks,
# you need to test your file in mLocust to confirm how many
# users each worker can support, e.g. confirm that the worker's CPU
# doesn't exceed 90%. Once you figure out the user/worker ratio,
# you should be able to figure out how many total workers you'll need
# to satisfy your performance requirements.
#
# These Mimesis locust files can be multi-use, 
# saturating a database with data or demonstrating standard workloads.
#
########################################################################

# Allows us to make many pymongo requests in parallel to overcome the single threaded problem
import gevent
_ = gevent.monkey.patch_all()

########################################################################
# TODO Add any additional imports here.
# TODO But make sure to include in requirements.txt
########################################################################
import pymongo
from bson import json_util
from bson.json_util import loads
from bson import ObjectId
from bson.decimal128 import Decimal128
from locust import User, events, task, constant, tag, between, runners
import time
from pickle import TRUE
from datetime import datetime, timedelta
import random
from decimal import Decimal
import string
from mimesis import Field, Fieldset, Schema
from mimesis.enums import Gender, TimestampFormat
from mimesis.locales import Locale
import json

# Global vars
# We can use this var to track the seq index of the worker in case we want to use it for generating unique seq keys in mimesis
_WORKER_ID = None
# Store the client conn globally so we don't create a conn pool for every user
# Track the srv globally so we know if we need to reinit the client
_CLIENT = None
_SRV = None
# Track the full host path so we know if anything changes
_HOST = None

@events.init.add_listener
def on_locust_init(environment, **_kwargs):
    global _WORKER_ID
    if not isinstance(environment.runner, runners.MasterRunner):
        _WORKER_ID = environment.runner.worker_index

# Mimesis global vars
# TODO Change the locale if needed
_ = Field(locale=Locale.EN)
_FS = Fieldset(locale=Locale.EN)
_SCHEMA = None

class MetricsLocust(User):
    ########################################################################
    # Class variables. 
    # The values are initialized with None
    # till they get set from the actual locust exeuction 
    # when the host param is passed in.
    # DO NOT HARDCODE VARS! PASS THEM IN VIA HOST PARAM.
    # TODO Do you have more than 20 tasks? If so, change the array init below.
    ########################################################################
    client, coll, bulk_size = None, None, None

    def __init__(self, parent):
        global _, _FS, _SCHEMA, _WORKER_ID, _HOST, _CLIENT, _SRV

        super().__init__(parent)

        try:
            vars = self.host.split("|")
            srv = vars[0]
            print("SRV:",srv)

            isInit = (_HOST != self.host)
            if isInit:
                print("Initializing...")
                self.client = pymongo.MongoClient(srv)
                _CLIENT = self.client
                _SRV = srv
                _HOST = self.host
            else:
                self.client = _CLIENT

            db = self.client[vars[1]]
            self.coll = db[vars[2]]

            # docs to insert per batch insert
            self.bulk_size = int(vars[3])
            print("Batch size from Host:",self.bulk_size)

            # init schema once
            if isInit:
                ########################################################################
                # mimesis schema for bulk creation
                # The zoneKey is a great way to demonstrate zone sharding,
                # e.g. all docs created by worker1 goes into shard1
                # and all docs created by worker2 goes into shard2
                # Note that increment doesn't maintain unique sequence numbers 
                # if you are running multiple mlocust users in parallel on the same worker
                # Not every api func has been used. The full api can be found here. https://mimesis.name/en/master/api.html
                # TODO Only use what you need. The more logic you have the slower your schema generation will be.
                ########################################################################
                # TODO modify how much you want to offset the increment by using the worker id
                # BUILT USING MIMESIS 17.0.0 to get rid of offensive words.
                _SCHEMA = Schema(
    schema=lambda: {
        "metadata_id": _("random.generate_string_by_mask", mask="##@@#@##@@@##@##@#@@@@@#", char="@", digit="#"),
        "consolidation_info": json.loads(_("random.weighted_choice", choices={
            '{"consolidation_type":{"S":"COUNT"},"ttl":{"S":"12"},"enabled":{"BOOL":true},"time_window_seconds":{"N":"900"}}': 25,
            '{"consolidation_type":{"S":"COUNT"},"sort_info":{"M":{"sort_order":{"S":"ASC"},"event_field":{"S":"appointment.start_at"},"field_format":{"S":"ISO_DATETIME"}}},"enabled":{"BOOL":true},"time_window_seconds":{"N":"900"}}': 50,
            '{"consolidation_type":{"S":"COUNT"},"ttl":{"N":"12"},"enabled":{"BOOL":true},"time_window_seconds":{"N":"900"}}': 25
        })),
        "created_at": _("datetime.datetime", start=2000, end=2023),
        "latest_version_for_type": _("random.weighted_choice", choices={'EMAIL': 20, 'PUSH': 20, 'SLACK': 20, 'SMS': 20, 'INBOX': 20}),
        "message_name": _("random.generate_string_by_mask", mask="test_metadata__@@@__#####", char="@", digit="#"),
        "message_source": _("random.weighted_choice", choices={'CS': 20, 'COMMUNICATIONS': 20, 'VS': 20, 'CG': 20, 'CHARGING': 20}),
        "metadata_info": json.loads(_("random.weighted_choice", choices={
            '{"reply_to_email":{"S":"test@rivian.com"},"from_email":{"S":"test@rivian.com"},"appointment_status":{"L":[{"S":"test_appointment_status"}]},"activity_type":{"L":[{"S":"test_activity_type"}]},"consumer_type":{"L":[{"S":"test_consumer_type"}]},"source":{"L":[{"S":"cs"}]},"activity_code":{"L":[{"S":"test_activity_code"}]},"from_name":{"S":"newman-tests"},"time_delta":{"L":[{"S":"1d"}]}}': 20,
            '{"event_type":{"L":[{"S":"coresvcs_ams_appointment"}]},"appointment_status":{"L":[{"S":"scheduled"}]},"activity_type":{"L":[{"S":"vehicle_service"}]},"event_name":{"L":[{"S":"created"}]},"action":{"L":[{"S":"appointment_scheduled"}]},"activity_code":{"L":[{"S":"fleet_job"},{"S":"fleet_mobile_job"}]},"source":{"L":[{"S":"ams"},{"S":"location"},{"S":"customer"},{"S":"dc-service-coreservice-scheduler"},{"S":"default"},{"S":"default_calculated"},{"S":"custom"},{"S":"calculated"}]}}': 20,
            '{"action":{"L":[{"S":"appointment_reminder"}]},"activity_code":{"L":[{"S":"test_drive_r1s"},{"S":"test_drive_r1t"},{"S":"r1t_md_d_a"},{"S":"r1s_md_d_a"},{"S":"r1t_dd_d_a"},{"S":"r1s_dd_d_a"}]},"source":{"L":[{"S":"ams"}]},"appointment_status":{"L":[{"S":"scheduled"}]},"activity_type":{"L":[{"S":"test_drive"}]}}': 20,
            '{"activity_type":{"L":[{"S":"test1"}]}}': 20,
            '{"event_type":{"L":[{"S":"coresvcs_ams_appointment"}]},"appointment_status":{"L":[{"S":"checked_in"}]},"activity_type":{"L":[{"S":"vehicle_service"}]},"event_name":{"L":[{"S":"status_changed"}]},"activity_code":{"L":[{"S":"fleet_job"},{"S":"egress_concierge_dropoff"},{"S":"ingress_customer_dropoff"}]},"source":{"L":[{"S":"ams"},{"S":"location"},{"S":"customer"},{"S":"default"},{"S":"default_calculated"},{"S":"custom"},{"S":"calculated"},{"S":"other"}]},"changed_fields":{"L":[{"S":"appointment.appointment_status"}]}}': 20
        })),
        "mobile_app_name": _("random.weighted_choice", choices={'CONSUMER': 50, 'HUB': 50}),
        "notes": _("random.weighted_choice", choices={'Updated notes': 20, 'Placeholder notes': 20, 'notes': 20, 'new notes': 20, 'Placeholder notes - updated for test': 20}),
        "notification_type": _("random.weighted_choice", choices={'EMAIL': 20, 'PUSH': 20, 'SLACK': 20, 'SMS': 20, 'INBOX': 20}),
        "notification_type_template_version": _("random.generate_string_by_mask", mask="EMAIL#@@@@", char="@", digit="#"),
        "pinpoint_app_name": _("random.weighted_choice", choices={'MESSAGE_PROVIDER_APP_ID': 50, 'HUB_PROVIDER_APP_ID': 50}),
        "preference_ids": json.loads(_("random.weighted_choice", choices={
            '[{"S":"9e2f0f78-250e-4421-a17c-5cf7e2f8237d"}]': 20,
            '[{"S":"0d24b4cc-2393-4f15-b861-24e3ae169593"}]': 20,
            '[{"S":"c464d56c-3ce9-460f-8fc7-8152759b5f86"}]': 20,
            '[{"S":"b172b5c3-86cd-4569-8e82-4194c9566403"}]': 20,
            '[{"S":"ac0c16de-545f-476e-8103-3a001c46799c"}]': 20
        })),
        "recipient_group": _("random.weighted_choice", choices={'DEFAULT': 50, '': 50}),
        "recipient_type": json.loads(_("random.weighted_choice", choices={
            '[{"S":"default"}]': 20,
            '[{"S":"recipient_type_1"}]': 20,
            '[{"S":"test"}]': 20,
            '[{"S":"default"},{"S":"guest"}]': 20,
            '[{"S":"recipient_type_1"},{"S":"recipient_type_2"}]': 20
        })),
        "recipient_type_attribute": _("random.weighted_choice", choices={'DEFAULT': 50, '': 50}),
        "template_id": _("random.weighted_choice", choices={
            'pre-order-confirmation.json': 20,
            'appointment-reminder-1day.json': 20,
            'updated_template.json': 20,
            'aggregated-message-test-template.json': 20,
            'fleet-report-ready-fleetos-en-us.json': 20
        }),
        "template_processor": _("random.weighted_choice", choices={'PINPOINT': 25, 'PINPOINT2': 25, 'PINPOINT3': 50}),
        "template_provider": _("random.weighted_choice", choices={'PINPOINT': 25, 'TEMPLATE_API': 25, 'WATERBOY_API': 50}),
        "template_version": _("numeric.integer_number", start=-1000, end=1000),
        "transform_event_mapping": json.loads(_("random.weighted_choice", choices={
            '[{"M":{"recipient_type":{"S":"default"},"event_field":{"S":"appointment.rivian_id"},"messaging_field":{"S":"push_data_payload"},"push_data_property":{"S":"andy_testing"}}}]': 20,
            '[{"M":{"recipient_type":{"S":"default"},"messaging_field":{"S":"push_data_payload"},"push_data_property":{"S":"andy_testing"},"event_field":{"S":"appointment.rivian_id"}}}]': 20,
            '[{"M":{"messaging_field":{"S":"messaging"},"event_field":{"S":"event"}}}]': 20,
            '[{"M":{"event_field":{"S":"event"},"messaging_field":{"S":"messaging"}}}]': 20,
            '[{"M":{"recipient_type":{"S":"default"},"event_field":{"S":"event"},"messaging_field":{"S":"messaging"}}}]': 20
        })),
        "updated_at": _("datetime.datetime", start=2000, end=2023),
    },
    iterations=self.bulk_size
)
        except Exception as e:
            # If an exception is caught, Locust will show a task with the error msg in the UI for ease
            events.request.fire(request_type="Host Init Failure", name=str(e), response_time=0, response_length=0, exception=e)
            raise e

    ################################################################
    # Example helper function that is not a Locust task.
    # All Locust tasks require the @task annotation
    ################################################################
    def get_time(self):
        return time.time()

    ################################################################
    # Since the loader is designed to be single threaded with 1 user
    # There's no need to set a weight to the task.
    # Do not create additional tasks in conjunction with the loader
    # If you are testing running queries while the loader is running
    # deploy 2 clusters in mLocust with one running faker and the
    # other running query tasks
    # The reason why we don't want to do both loads and queries is
    # because of the simultaneous users and wait time between
    # requests. The bulk inserts can take longer than 1s possibly
    # which will cause the workers to fall behind.
    ################################################################
    @task(1)
    def _bulkinsert(self):
        global _SCHEMA 

        # Note that you don't pass in self despite the signature above
        tic = self.get_time();
        name = "bulkInsert";
 
        try:
            # If you want to do an insert_one, you need to grab the first array element of schema, e.g. (schema*1)[0]
            self.coll.insert_many(_SCHEMA.create(), ordered=False)

            events.request.fire(request_type="mlocust", name=name, response_time=(self.get_time()-tic)*1000, response_length=0)
        except Exception as e:
            events.request.fire(request_type="mlocust", name=name, response_time=(self.get_time()-tic)*1000, response_length=0, exception=e)
            # Add a sleep so we don't overload the system with exceptions
            time.sleep(5)
