# -*- coding: utf-8 -*-
# Copyright © 2019 SparkMeter, Inc.
# All Rights Reserved.
"""API v0 event views."""
import http.client

from flask_security import roles_accepted

from sparkmeter.api.apiviews0 import api, success
from sparkmeter.event.eventdomain import Event
from sparkmeter.exceptions import APIError


@api.route('/event/<uuid:event_id>')
@roles_accepted('api')
def get_event(event_id):
    """Get event status.
    ---
   parameters:
    - name: event_id
      in: path
      description: The ID of the event
      required: true
      schema:
        type: string
        format: uuid
    get:
      summary: get the status of an event
      description: >
        This call requests the status of a system event by ID. Based on the
        event type, the payload can contain additional event-specific
        information.


        _Typical use cases:_

        * Determine when a customer wallet zero event has been processed.
      responses:
        200:
          description: the status of the event
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/EventStatusModel'
              examples:
                Base:
                  value:
                    error: null
                    status: success
                    event:
                      id: e2b94357-4b34-4871-86ef-51745a6247d4
                      created: '2013-01-01T01:01:01'
                      status: pending
                Customer Wallet:
                  value:
                    error: null
                    status: success
                    event:
                      id: e2b94357-4b34-4871-86ef-51745a6247d4
                      created: '2013-01-01T01:01:01'
                      status: pending
                      customer: 063d4c95-c3af-4bef-9941-16305da1c96e
                      wallet: credit
    """
    event = Event.get_by_id(event_id)
    if event is None:
        raise APIError('no such event', status_code=http.client.NOT_FOUND)
    return success(event=event.to_json(), type=event.get_info().label)


# These are OpenAPI docs for assorted model objects. Once we pick a doc framework to use, they should
#   be integrated.
"""
components:
  schemas:
    EventModel:
      type: object
      description: a base event response object
      required:
        - created
        - id
        - status
      properties:
        id:
          type: string
          description: the ID of the event
          format: uuid
        created:
          type: string
          description: the time the event was created
          format: date-time
        status:
          type: string
          description: the state of the event
          enum: ['processed', 'pending']
    CustomerWalletEventModel:
      type: object
      description: a wallet event response object
      allOf:
        - $ref: '#/components/schemas/EventModel'
        - type: object
          required:
            - customer
            - wallet
          properties:
            customer:
              type: string
              description: the system ID of the customer
              format: uuid
            wallet:
              type: string
              description: the customer wallet associated with the event
              enum: ['credit', 'plan', 'debt']
    ResponseModel:
      type: object
      required:
        - error
        - status
      properties:
        error:
          type: string
          nullable: true
          description: an optional error message
        status:
          type: string
          description: whether or not the request was successful
          enum: ['success', 'error']
    EventStatusModel:
      description: the event's status
      allOf:
        - $ref: '#/components/schemas/ResponseModel'
        - type: object
          required:
            - type
            - event
          properties:
            type:
              type: string
              description: the event type
            event:
              type: object
              description: detailed information about the event
              oneOf:
                - $ref: '#/components/schemas/EventModel'
                - $ref: '#/components/schemas/CustomerWalletEventModel'
              discriminator:
                propertyName: type
"""
