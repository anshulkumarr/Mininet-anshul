import json
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER
from ryu.controller.handler import set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet
from ryu.lib.packet import ethernet
from ryu.lib.packet import ether_types
from ryu.lib.packet import ipv4
from ryu.lib.packet import arp


class TrafficSlicing(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(TrafficSlicing, self).__init__(*args, **kwargs)

        # out_port = slice_to_port[ip.src][ip.dst]
        self.slice_to_port =  {
            '10.0.0.1':{
            	'10.0.0.2': 2,
            	'10.0.0.3': 2
            		},
            '10.0.0.2':{ 
            	'10.0.0.1': 1,
            	'10.0.0.3': 3 
            	},
            '10.0.0.3':{ 
            	'10.0.0.1': 1,
            	'10.0.0.2': 2
            	}
            	} 
         

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # install the table-miss flow entry.
        match = parser.OFPMatch()
        actions = [
            parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)
        ]
        #self.logger.info("add_flow(%s, 0, %s, %s", json.dumps(datapath), json.dumps(match), json.dumps(actions))
        actions_str=[a.port for a in actions]
        self.add_flow(datapath, 0, match, actions)

    def add_flow(self, datapath, priority, match, actions):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        # construct flow_mod message and send it.
        inst = [parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(
            datapath=datapath, priority=priority, match=match, instructions=inst
        )
        self.logger.info("add_flow.datapath.send_msg(%s)", vars(mod))
        datapath.send_msg(mod)

    def _send_package(self, msg, datapath, in_port, actions):
        data = None
        ofproto = datapath.ofproto
        if msg.buffer_id == ofproto.OFP_NO_BUFFER:
            data = msg.data

        out = datapath.ofproto_parser.OFPPacketOut(
            datapath=datapath,
            buffer_id=msg.buffer_id,
            in_port=in_port,
            actions=actions,
            data=data,
        )
        self.logger.info("_send_package.datapath.send_msg(%s)", vars(out))
        datapath.send_msg(out)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def _packet_in_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        in_port = msg.match["in_port"]
        pkt = packet.Packet(msg.data)
        dpid = datapath.id
        ip = pkt.get_protocols(ipv4.ipv4)[0]
        dst=ip.dst
        src=ip.src
        
	
	
        out_port = self.slice_to_port[src][dst]
        actions = [datapath.ofproto_parser.OFPActionOutput(out_port)]
        match = datapath.ofproto_parser.OFPMatch(ipv4_src=src)

        self.add_flow(datapath, 1, match, actions)
        self._send_package(msg, datapath, in_port, actions)
